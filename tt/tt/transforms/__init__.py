"""Transform pipeline for TypeScript to Python conversion."""
from __future__ import annotations

from . import syntax, control_flow, expressions, libraries


def apply_all(source: str) -> str:
    """Apply all transforms in sequence."""
    code = source
    code = syntax.apply(code)
    code = control_flow.apply(code)
    code = expressions.apply(code)
    code = libraries.apply(code)
    return code
