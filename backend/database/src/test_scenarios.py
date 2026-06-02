"""
Predefined portfolio test scenarios for demos and CLI reset.

Each scenario pairs holdings with retirement goals so analysis is more coherent.
All ETF symbols must exist in seed_data.py unless listed in EXTRA_INSTRUMENTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .schemas import InstrumentCreate

DEFAULT_SCENARIO = "balanced"

# Individual stocks not in seed_data.py (populate adds these if missing)
EXTRA_INSTRUMENTS: Dict[str, Dict[str, Any]] = {
    "AAPL": {
        "name": "Apple Inc.",
        "type": "stock",
        "current_price": 195.89,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"technology": 100},
        "allocation_asset_class": {"equity": 100},
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "type": "stock",
        "current_price": 178.35,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"consumer_discretionary": 100},
        "allocation_asset_class": {"equity": 100},
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "type": "stock",
        "current_price": 522.74,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"technology": 100},
        "allocation_asset_class": {"equity": 100},
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "type": "stock",
        "current_price": 430.82,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"technology": 100},
        "allocation_asset_class": {"equity": 100},
    },
    "GOOGL": {
        "name": "Alphabet Inc. Class A",
        "type": "stock",
        "current_price": 173.69,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"technology": 100},
        "allocation_asset_class": {"equity": 100},
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "type": "stock",
        "current_price": 248.50,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"consumer_discretionary": 100},
        "allocation_asset_class": {"equity": 100},
    },
}


@dataclass(frozen=True)
class TestScenario:
    id: str
    name: str
    description: str
    years_until_retirement: int
    target_retirement_income: int
    accounts: Tuple[Dict[str, Any], ...]


SCENARIOS: Dict[str, TestScenario] = {
    "balanced": TestScenario(
        id="balanced",
        name="Balanced retirement",
        description="Three-account mix of US equity, bonds, and international (~$90k). Goals match a mid-career saver.",
        years_until_retirement=22,
        target_retirement_income=48_000,
        accounts=(
            {
                "name": "401(k)",
                "purpose": "Primary retirement savings with employer match",
                "cash": 5_000.0,
                "positions": [("SPY", 80), ("BND", 120), ("VEA", 60)],
            },
            {
                "name": "Roth IRA",
                "purpose": "Tax-free growth with moderate risk",
                "cash": 2_500.0,
                "positions": [("QQQ", 40), ("AGG", 50), ("GLD", 15)],
            },
            {
                "name": "Taxable Brokerage",
                "purpose": "Flexible investing outside retirement accounts",
                "cash": 3_000.0,
                "positions": [("IWM", 30), ("VNQ", 25), ("VIG", 35)],
            },
        ),
    ),
    "conservative": TestScenario(
        id="conservative",
        name="Conservative / near income",
        description="Bond-heavy portfolio for lower volatility (~$95k). Shorter horizon and modest income target.",
        years_until_retirement=12,
        target_retirement_income=42_000,
        accounts=(
            {
                "name": "Traditional IRA",
                "purpose": "Capital preservation and income",
                "cash": 8_000.0,
                "positions": [("BND", 200), ("AGG", 150), ("TLT", 40)],
            },
            {
                "name": "Taxable Bond Ladder",
                "purpose": "Stable taxable fixed income",
                "cash": 5_000.0,
                "positions": [("HYG", 60), ("SPY", 25), ("VIG", 30)],
            },
        ),
    ),
    "aggressive_growth": TestScenario(
        id="aggressive_growth",
        name="Aggressive growth",
        description="Equity-tilted ETFs with higher growth focus (~$105k). Long horizon, moderate income goal.",
        years_until_retirement=28,
        target_retirement_income=55_000,
        accounts=(
            {
                "name": "Brokerage",
                "purpose": "Growth-oriented taxable account",
                "cash": 4_000.0,
                "positions": [("QQQ", 100), ("XLK", 80), ("VUG", 60), ("SPY", 40)],
            },
            {
                "name": "Roth IRA",
                "purpose": "Aggressive tax-advantaged growth",
                "cash": 2_000.0,
                "positions": [("IWM", 50), ("VWO", 45), ("XLE", 30)],
            },
        ),
    ),
    "near_retirement": TestScenario(
        id="near_retirement",
        name="Near retirement",
        description="Larger, income-oriented book (~$175k). Five years to retirement with a realistic withdrawal target.",
        years_until_retirement=5,
        target_retirement_income=38_000,
        accounts=(
            {
                "name": "401(k)",
                "purpose": "Pre-retirement de-risking",
                "cash": 12_000.0,
                "positions": [("BND", 280), ("AGG", 180), ("VIG", 70)],
            },
            {
                "name": "Roth IRA",
                "purpose": "Supplemental retirement assets",
                "cash": 6_000.0,
                "positions": [("SPY", 50), ("VNQ", 40), ("GLD", 20)],
            },
        ),
    ),
    "simple_starter": TestScenario(
        id="simple_starter",
        name="Simple starter",
        description="Single account, two ETFs (~$28k). Early career with a long horizon and modest income goal.",
        years_until_retirement=35,
        target_retirement_income=35_000,
        accounts=(
            {
                "name": "Starter IRA",
                "purpose": "First retirement account",
                "cash": 2_000.0,
                "positions": [("SPY", 25), ("BND", 40)],
            },
        ),
    ),
    "tech_stocks": TestScenario(
        id="tech_stocks",
        name="Tech stocks + ETFs",
        description="Concentrated mega-cap tech plus core ETFs (~$120k). Good for testing risk concentration warnings.",
        years_until_retirement=20,
        target_retirement_income=50_000,
        accounts=(
            {
                "name": "401(k)",
                "purpose": "Core retirement with index funds",
                "cash": 5_000.0,
                "positions": [("SPY", 60), ("BND", 80), ("QQQ", 30)],
            },
            {
                "name": "Tech Brokerage",
                "purpose": "Individual technology holdings",
                "cash": 8_000.0,
                "positions": [
                    ("AAPL", 40),
                    ("MSFT", 25),
                    ("NVDA", 15),
                    ("GOOGL", 20),
                    ("AMZN", 12),
                    ("TSLA", 10),
                ],
            },
        ),
    ),
    "legacy_simple": TestScenario(
        id="legacy_simple",
        name="Basic 401(k) demo",
        description="Single 401(k) with five ETF positions and empty satellite accounts.",
        years_until_retirement=25,
        target_retirement_income=100_000,
        accounts=(
            {
                "name": "401(k)",
                "purpose": "Primary retirement savings",
                "cash": 5_000.0,
                "positions": [("SPY", 100), ("QQQ", 50), ("BND", 200), ("VEA", 150), ("GLD", 25)],
            },
            {
                "name": "Roth IRA",
                "purpose": "Tax-free retirement savings",
                "cash": 1_000.0,
                "positions": [],
            },
            {
                "name": "Taxable Brokerage",
                "purpose": "General investment account",
                "cash": 2_500.0,
                "positions": [],
            },
        ),
    ),
}


def list_scenarios() -> List[Dict[str, str]]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
        }
        for s in SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> TestScenario:
    key = scenario_id or DEFAULT_SCENARIO
    if key not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario '{scenario_id}'. Choose one of: {valid}")
    return SCENARIOS[key]


def _symbols_in_scenario(scenario: TestScenario) -> set[str]:
    symbols: set[str] = set()
    for account in scenario.accounts:
        for symbol, _qty in account["positions"]:
            symbols.add(symbol)
    return symbols


def ensure_extra_instruments(db, logger=None) -> None:
    """Insert individual stocks used by some scenarios if not already seeded."""
    log = logger.info if logger else print
    for symbol, info in EXTRA_INSTRUMENTS.items():
        if db.instruments.find_by_symbol(symbol):
            continue
        try:
            instrument_data = InstrumentCreate(
                symbol=symbol,
                name=info["name"],
                instrument_type=info["type"],
                current_price=Decimal(str(info["current_price"])),
                allocation_regions=info["allocation_regions"],
                allocation_sectors=info["allocation_sectors"],
                allocation_asset_class=info["allocation_asset_class"],
            )
            db.instruments.create_instrument(instrument_data)
            log(f"Added instrument: {symbol}")
        except Exception as exc:
            if logger:
                logger.warning("Could not add instrument %s: %s", symbol, exc)
            else:
                print(f"Warning: Could not add instrument {symbol}: {exc}")


def apply_scenario(db, clerk_user_id: str, scenario_id: str = DEFAULT_SCENARIO) -> Dict[str, Any]:
    """
    Set user retirement goals and create accounts/positions for a scenario.
    Caller should ensure the user has no existing accounts (or reset first).
    """
    scenario = get_scenario(scenario_id)
    needed = _symbols_in_scenario(scenario)
    if needed & set(EXTRA_INSTRUMENTS):
        ensure_extra_instruments(db)

    db.users.db.update(
        "users",
        {
            "years_until_retirement": scenario.years_until_retirement,
            "target_retirement_income": scenario.target_retirement_income,
        },
        "clerk_user_id = :clerk_user_id",
        {"clerk_user_id": clerk_user_id},
    )

    created_accounts = []
    for account_data in scenario.accounts:
        account_id = db.accounts.create_account(
            clerk_user_id=clerk_user_id,
            account_name=account_data["name"],
            account_purpose=account_data["purpose"],
            cash_balance=Decimal(str(account_data["cash"])),
        )
        for symbol, quantity in account_data["positions"]:
            db.positions.add_position(
                account_id=account_id,
                symbol=symbol,
                quantity=Decimal(str(quantity)),
            )
        created_accounts.append(account_id)

    all_accounts = []
    for account_id in created_accounts:
        account = db.accounts.find_by_id(account_id)
        account["positions"] = db.positions.find_by_account(account_id)
        all_accounts.append(account)

    return {
        "scenario": scenario.id,
        "scenario_name": scenario.name,
        "message": f"Loaded '{scenario.name}' test portfolio",
        "accounts_created": len(created_accounts),
        "accounts": all_accounts,
        "years_until_retirement": scenario.years_until_retirement,
        "target_retirement_income": scenario.target_retirement_income,
    }
