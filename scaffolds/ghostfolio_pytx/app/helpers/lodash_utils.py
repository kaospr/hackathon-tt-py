"""Lodash-equivalent utility functions for Python."""
from __future__ import annotations

import copy


def clone_deep(obj):
    """Deep copy an object."""
    return copy.deepcopy(obj)


def sort_by(arr: list, key_fn) -> list:
    """Sort list by key function, returning new list."""
    return sorted(arr, key=key_fn)


def uniq_by(arr: list, key: str) -> list:
    """Deduplicate list by a key attribute/dict-key."""
    seen = set()
    result = []
    for item in arr:
        k = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def is_number(x) -> bool:
    """Check if value is a number."""
    return isinstance(x, (int, float))


def get_sum(items) -> float:
    """Sum Big or numeric values."""
    total = 0
    for item in items:
        if hasattr(item, "toNumber"):
            total += item.toNumber()
        elif isinstance(item, (int, float)):
            total += item
    return total
