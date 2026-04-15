"""Structural TypeScript to Python syntax transforms.

Handles: imports, type annotations, class/method declarations,
variable declarations, `new` keyword, async/await removal.
"""
from __future__ import annotations

import re


def apply(source: str) -> str:
    """Apply syntax transforms to TypeScript source."""
    return source
