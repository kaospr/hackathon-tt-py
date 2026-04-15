"""Control flow transforms: for loops, if/else, ternary, switch/case.

Converts brace-delimited blocks to Python indentation-based blocks.
"""
from __future__ import annotations

import re


def apply(source: str) -> str:
    """Apply control flow transforms to source."""
    return source
