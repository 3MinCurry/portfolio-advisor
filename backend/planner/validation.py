"""Post-analysis validation — flag contradictions between agent outputs."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

OPTIMISTIC_PHRASES = (
    "on track",
    "well positioned",
    "well-positioned",
    "excellent",
    "strong retirement",
    "comfortable retirement",
    "highly likely",
    "very likely to meet",
)

LOW_RISK_PHRASES = ("low risk", "minimal risk", "well diversified", "highly diversified")


def _report_mentions_number(report: str, value: float) -> bool:
    """True if the report text includes the value in common formatted forms."""
    if value is None:
        return True
    try:
        num = float(value)
    except (TypeError, ValueError):
        return True
    candidates = {
        f"{num:.0f}",
        f"{num:.1f}".rstrip("0").rstrip("."),
        f"{num:,.0f}",
        f"{num:,.2f}",
    }
    return any(c in report for c in candidates if c)


def validate_job_outputs(job: dict[str, Any]) -> list[str]:
    """
    Compare structured agent metrics against the narrative report.
    Returns human-readable warnings (empty if consistent).
    """
    warnings: list[str] = []

    report = ((job.get("report_payload") or {}).get("content") or "").lower()
    if not report:
        return warnings

    retirement = job.get("retirement_payload") or {}
    risk = job.get("risk_payload") or {}

    monte_carlo = (retirement.get("metrics") or {}).get("monte_carlo") or {}
    retirement_metrics = retirement.get("metrics") or {}
    success_rate = monte_carlo.get("success_rate")
    if success_rate is not None:
        try:
            rate = float(success_rate)
        except (TypeError, ValueError):
            rate = None
        if rate is not None:
            if not _report_mentions_number(report, rate):
                warnings.append(
                    f"Reporter narrative may not cite Monte Carlo success rate ({rate}%)."
                )
        if rate is not None and rate < 50:
            if any(phrase in report for phrase in OPTIMISTIC_PHRASES):
                warnings.append(
                    f"Reporter narrative sounds optimistic but Monte Carlo success rate is {rate}%."
                )

    risk_metrics = risk.get("metrics") or {}
    portfolio_value = retirement_metrics.get("portfolio_value")
    if portfolio_value and not _report_mentions_number(report, float(portfolio_value)):
        warnings.append(
            f"Reporter narrative may not cite portfolio value (${float(portfolio_value):,.0f})."
        )

    risk_level = (risk_metrics.get("risk_level") or "").lower()
    if risk_level in ("high", "elevated"):
        if any(phrase in report for phrase in LOW_RISK_PHRASES):
            warnings.append(
                f"Reporter narrative understates risk; Risk Manager rated portfolio as {risk_level}."
            )

    retirement_analysis = (retirement.get("analysis") or "").lower()
    if success_rate is not None and retirement_analysis:
        try:
            rate = float(success_rate)
        except (TypeError, ValueError):
            rate = None
        if rate is not None and rate < 50:
            if any(phrase in retirement_analysis for phrase in OPTIMISTIC_PHRASES):
                warnings.append(
                    f"Retirement narrative sounds optimistic but Monte Carlo success rate is {rate}%."
                )

    for warning in warnings:
        logger.warning("Job %s validation: %s", job.get("id"), warning)

    return warnings


def retirement_readiness_label(success_rate: float | None) -> str:
    """Map Monte Carlo success rate to a short readiness label."""
    if success_rate is None:
        return "unknown"
    if success_rate >= 70:
        return "on_track"
    if success_rate >= 50:
        return "moderate"
    if success_rate >= 25:
        return "at_risk"
    return "critical"
