"""Deterministic analysis pipeline — agents run in a fixed order."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent import (
    invoke_charter_internal,
    invoke_reporter_internal,
    invoke_retirement_internal,
    invoke_risk_internal,
)
from validation import validate_job_outputs

logger = logging.getLogger(__name__)


async def run_analysis_pipeline(
    job_id: str, portfolio_summary: dict[str, Any], db
) -> list[str]:
    """
    Run specialist agents in a fixed order so Reporter sees structured outputs.

    Order:
      1. Charter + Risk + Retirement (parallel when applicable)
      2. Reporter (last — reads retirement/risk metrics from DB)
      3. Validation
    """
    num_positions = portfolio_summary.get("num_positions", 0)
    if num_positions <= 0:
        logger.info("Planner: No positions — skipping agent pipeline")
        return []

    parallel: list = []

    if num_positions >= 2:
        parallel.append(invoke_charter_internal(job_id))

    parallel.append(invoke_risk_internal(job_id))
    parallel.append(invoke_retirement_internal(job_id))

    if parallel:
        await asyncio.gather(*parallel)

    await invoke_reporter_internal(job_id)

    job = db.jobs.find_by_id(job_id)
    warnings = validate_job_outputs(job) if job else []

    if warnings:
        db.jobs.update_summary(
            job_id,
            {
                "validation_warnings": warnings,
                "pipeline": "deterministic",
            },
        )

    return warnings
