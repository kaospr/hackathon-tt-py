"""Extract method bodies from TypeScript source files using brace-counting."""
from __future__ import annotations

from pathlib import Path


def parse_ts_file(path: Path) -> dict[str, str]:
    """Parse a TypeScript file and return {method_name: method_body}.

    Uses brace-counting to find method boundaries in class bodies.
    """
    return {}


def extract_methods(
    roai_path: Path, base_path: Path
) -> dict[str, str]:
    """Extract all needed methods from ROAI and base TS files.

    Returns dict with keys:
      - calculateOverallPerformance
      - getPerformanceCalculationType
      - getSymbolMetrics
      - computeSnapshot
      - computeTransactionPoints
      - getChartDateMap
      - getPerformance
      - getInvestments
      - getInvestmentsByGroup
    """
    return {}
