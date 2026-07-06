"""
Risk Management Agent - evaluates portfolio concentration and diversification risk.
"""

import os
import logging
from typing import Dict, Any, List, Tuple

from agents.extensions.models.litellm_model import LitellmModel
from src.portfolio import (
    calculate_portfolio_value,
    position_market_value,
    position_values_by_symbol,
)

logger = logging.getLogger()


def calculate_portfolio_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compute quantitative risk metrics from portfolio holdings."""
    position_values = position_values_by_symbol(portfolio_data)
    sector_values: Dict[str, float] = {}
    region_values: Dict[str, float] = {}
    asset_values: Dict[str, float] = {}
    total_value = calculate_portfolio_value(portfolio_data)

    for account in portfolio_data.get("accounts", []):
        cash = float(account.get("cash_balance") or 0)
        if cash > 0:
            asset_values["cash"] = asset_values.get("cash", 0) + cash

        for position in account.get("positions", []):
            value = position_market_value(position)
            if value <= 0:
                continue

            instrument = position.get("instrument") or {}
            for sector, pct in (instrument.get("allocation_sectors") or {}).items():
                sector_values[sector] = sector_values.get(sector, 0) + value * (float(pct) / 100.0)

            for region, pct in (instrument.get("allocation_regions") or {}).items():
                region_values[region] = region_values.get(region, 0) + value * (float(pct) / 100.0)

            for asset, pct in (instrument.get("allocation_asset_class") or {}).items():
                asset_values[asset] = asset_values.get(asset, 0) + value * (float(pct) / 100.0)

    if total_value <= 0:
        return {
            "total_value": 0,
            "position_count": 0,
            "top_holding_symbol": None,
            "top_holding_pct": 0,
            "top_sector": None,
            "top_sector_pct": 0,
            "top_region": None,
            "top_region_pct": 0,
            "equity_pct": 0,
            "fixed_income_pct": 0,
            "cash_pct": 0,
            "herfindahl_positions": 0,
            "risk_level": "unknown",
        }

    def top_share(weights: Dict[str, float]) -> Tuple[str | None, float]:
        if not weights:
            return None, 0.0
        symbol, value = max(weights.items(), key=lambda x: x[1])
        return symbol, round(100 * value / total_value, 1)

    def herfindahl(weights: Dict[str, float]) -> float:
        if not weights:
            return 0.0
        shares = [v / total_value for v in weights.values()]
        return round(sum(s * s for s in shares), 4)

    top_symbol, top_pct = top_share(position_values)
    top_sector, top_sector_pct = top_share(sector_values)
    top_region, top_region_pct = top_share(region_values)

    equity_pct = round(100 * asset_values.get("equity", 0) / total_value, 1)
    fixed_income_pct = round(100 * asset_values.get("fixed_income", 0) / total_value, 1)
    cash_pct = round(100 * asset_values.get("cash", 0) / total_value, 1)
    hhi = herfindahl(position_values)

    risk_level = "low"
    if top_pct >= 35 or hhi >= 0.25 or (equity_pct >= 90 and len(position_values) < 5):
        risk_level = "high"
    elif top_pct >= 25 or hhi >= 0.18 or equity_pct >= 80:
        risk_level = "elevated"
    elif top_pct >= 18 or hhi >= 0.12:
        risk_level = "moderate"

    sorted_holdings = sorted(position_values.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_value": round(total_value, 2),
        "position_count": len(position_values),
        "top_holding_symbol": top_symbol,
        "top_holding_pct": top_pct,
        "top_sector": top_sector,
        "top_sector_pct": top_sector_pct,
        "top_region": top_region,
        "top_region_pct": top_region_pct,
        "equity_pct": equity_pct,
        "fixed_income_pct": fixed_income_pct,
        "cash_pct": cash_pct,
        "herfindahl_positions": hhi,
        "risk_level": risk_level,
        "top_holdings": [
            {"symbol": s, "pct": round(100 * v / total_value, 1)}
            for s, v in sorted_holdings
        ],
    }


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db=None):
    """Create the risk agent task with pre-computed metrics."""
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region

    model = LitellmModel(model=f"bedrock/{model_id}")
    metrics = calculate_portfolio_metrics(portfolio_data)

    holdings_lines = "\n".join(
        f"  - {h['symbol']}: {h['pct']}%" for h in metrics.get("top_holdings", [])
    )

    task = f"""
# Portfolio Risk Metrics (Job {job_id})

## Summary
- Total portfolio value: ${metrics['total_value']:,.2f}
- Number of positions: {metrics['position_count']}
- Preliminary risk level (rules-based): {metrics['risk_level']}

## Concentration
- Largest holding: {metrics['top_holding_symbol']} at {metrics['top_holding_pct']}%
- Position concentration (HHI): {metrics['herfindahl_positions']}
- Top sector: {metrics['top_sector']} ({metrics['top_sector_pct']}%)
- Top region: {metrics['top_region']} ({metrics['top_region_pct']}%)

## Asset mix
- Equity: {metrics['equity_pct']}%
- Fixed income: {metrics['fixed_income_pct']}%
- Cash: {metrics['cash_pct']}%

## Top holdings
{holdings_lines or '  (none)'}

Write a risk management report in markdown. Include sections:
## Executive Summary
## Key Risk Factors
## Recommendations
## Overall Risk Level

State the overall risk level clearly as one of: low, moderate, elevated, high.
"""

    return model, [], task, metrics
