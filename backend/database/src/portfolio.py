"""Shared portfolio valuation utilities (used by all analysis agents)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def parse_price(instrument: Optional[Dict[str, Any]]) -> Optional[float]:
    """Return a positive price, or None if missing/invalid."""
    if not instrument:
        return None
    price = instrument.get("current_price")
    if price is None or price == "":
        return None
    try:
        value = float(price)
        return value if value > 0 else None
    except (TypeError, ValueError):
        return None


def position_market_value(position: Dict[str, Any]) -> float:
    """Market value of a position; skips positions without a valid price."""
    quantity = float(position.get("quantity", 0) or 0)
    if quantity <= 0:
        return 0.0
    price = parse_price(position.get("instrument") or {})
    if price is None:
        return 0.0
    return quantity * price


def calculate_portfolio_value(portfolio_data: Dict[str, Any]) -> float:
    """Total portfolio value (cash + priced positions)."""
    total = 0.0
    for account in portfolio_data.get("accounts", []):
        total += float(account.get("cash_balance", 0) or 0)
        for position in account.get("positions", []):
            total += position_market_value(position)
    return total


def collect_symbols_by_weight(portfolio_data: Dict[str, Any], limit: int = 8) -> List[str]:
    """Ticker symbols ordered by portfolio weight (largest first)."""
    weights: Dict[str, float] = {}
    for account in portfolio_data.get("accounts", []):
        for position in account.get("positions", []):
            symbol = position.get("symbol")
            if not symbol:
                continue
            value = position_market_value(position)
            if value > 0:
                weights[symbol] = weights.get(symbol, 0.0) + value
    return sorted(weights.keys(), key=lambda s: weights[s], reverse=True)[:limit]


def calculate_asset_allocation(portfolio_data: Dict[str, Any]) -> Dict[str, float]:
    """Asset-class weights as fractions of total portfolio value."""
    totals = {
        "equity": 0.0,
        "bonds": 0.0,
        "real_estate": 0.0,
        "commodities": 0.0,
        "alternatives": 0.0,
        "cash": 0.0,
    }
    total_value = 0.0

    for account in portfolio_data.get("accounts", []):
        cash = float(account.get("cash_balance", 0) or 0)
        totals["cash"] += cash
        total_value += cash

        for position in account.get("positions", []):
            value = position_market_value(position)
            if value <= 0:
                continue
            total_value += value
            instrument = position.get("instrument") or {}
            asset_class = instrument.get("allocation_asset_class") or {}
            totals["equity"] += value * float(asset_class.get("equity", 0)) / 100.0
            totals["bonds"] += value * float(asset_class.get("fixed_income", 0)) / 100.0
            totals["real_estate"] += value * float(asset_class.get("real_estate", 0)) / 100.0
            totals["commodities"] += value * float(asset_class.get("commodities", 0)) / 100.0
            totals["alternatives"] += value * float(asset_class.get("alternatives", 0)) / 100.0

    if total_value <= 0:
        return {k: 0.0 for k in totals}

    return {k: v / total_value for k, v in totals.items()}


def position_values_by_symbol(portfolio_data: Dict[str, Any]) -> Dict[str, float]:
    """Aggregate position values by ticker."""
    values: Dict[str, float] = {}
    for account in portfolio_data.get("accounts", []):
        for position in account.get("positions", []):
            symbol = position.get("symbol", "UNKNOWN")
            value = position_market_value(position)
            if value > 0:
                values[symbol] = values.get(symbol, 0.0) + value
    return values
