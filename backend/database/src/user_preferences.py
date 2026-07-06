"""Load retirement-related user preferences with consistent defaults."""

from __future__ import annotations

from typing import Any, Dict, Optional

DEFAULT_YEARS_UNTIL_RETIREMENT = 30
DEFAULT_TARGET_INCOME = 80_000.0
DEFAULT_CURRENT_AGE = 40
DEFAULT_ANNUAL_CONTRIBUTION = 10_000.0


def load_user_preferences(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize user row into preferences dict for retirement / reporter agents."""
    if not user:
        return {
            "years_until_retirement": DEFAULT_YEARS_UNTIL_RETIREMENT,
            "target_retirement_income": DEFAULT_TARGET_INCOME,
            "current_age": DEFAULT_CURRENT_AGE,
            "annual_contribution": DEFAULT_ANNUAL_CONTRIBUTION,
        }

    years = user.get("years_until_retirement")
    if years is None:
        years = DEFAULT_YEARS_UNTIL_RETIREMENT

    age = user.get("current_age")
    if age is None:
        age = max(18, 65 - int(years))

    contribution = user.get("annual_contribution")
    if contribution is None:
        contribution = DEFAULT_ANNUAL_CONTRIBUTION

    return {
        "years_until_retirement": int(years),
        "target_retirement_income": float(user.get("target_retirement_income", DEFAULT_TARGET_INCOME)),
        "current_age": int(age),
        "annual_contribution": float(contribution),
    }
