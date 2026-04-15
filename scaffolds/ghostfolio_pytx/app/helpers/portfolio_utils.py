"""Portfolio utility functions."""
from __future__ import annotations

INVESTMENT_ACTIVITY_TYPES = ["BUY", "SELL"]


def get_factor(activity_type: str) -> int:
    """Return quantity factor: +1 for BUY, -1 for SELL, 0 otherwise."""
    if activity_type == "BUY":
        return 1
    elif activity_type == "SELL":
        return -1
    return 0
