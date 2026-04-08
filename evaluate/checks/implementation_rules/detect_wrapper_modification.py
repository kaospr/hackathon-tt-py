#!/usr/bin/env python3
"""Detect modifications to the immutable wrapper layer.

The wrapper (app/wrapper/) and app/main.py in translations/ghostfolio_pytx
must be byte-for-byte identical to those in translations/ghostfolio_pytx_example.
TT must copy these files as-is and only place its translations inside
app/implementation/.

Exits non-zero if any wrapper file or main.py has been modified.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()

PYTX_DIR = PROJECT_ROOT / "translations" / "ghostfolio_pytx"
EXAMPLE_DIR = PROJECT_ROOT / "translations" / "ghostfolio_pytx_example"

# Files/dirs that must be identical
IMMUTABLE_PATHS = [
    "app/main.py",
    "app/wrapper",
]


def _collect_files(base: Path, rel_path: str) -> list[str]:
    """Collect all .py files under base/rel_path, returning relative paths."""
    full = base / rel_path
    if full.is_file():
        return [rel_path]
    if full.is_dir():
        return sorted(
            str(p.relative_to(base))
            for p in full.rglob("*.py")
            if "__pycache__" not in str(p)
        )
    return []


def check() -> list[str]:
    violations: list[str] = []

    if not PYTX_DIR.exists():
        violations.append(f"translations/ghostfolio_pytx does not exist")
        return violations
    if not EXAMPLE_DIR.exists():
        violations.append(f"translations/ghostfolio_pytx_example does not exist")
        return violations

    for rel in IMMUTABLE_PATHS:
        example_files = _collect_files(EXAMPLE_DIR, rel)
        pytx_files = _collect_files(PYTX_DIR, rel)

        # Check for missing files in pytx
        for f in example_files:
            pytx_file = PYTX_DIR / f
            example_file = EXAMPLE_DIR / f
            if not pytx_file.exists():
                violations.append(f"MISSING: {f} exists in example but not in ghostfolio_pytx")
                continue
            pytx_content = pytx_file.read_text(encoding="utf-8")
            example_content = example_file.read_text(encoding="utf-8")
            if pytx_content != example_content:
                violations.append(f"MODIFIED: {f} differs from example (wrapper must not be changed)")

        # Check for extra files in pytx wrapper
        for f in pytx_files:
            if f not in example_files:
                violations.append(f"EXTRA: {f} exists in ghostfolio_pytx but not in example")

    return violations


def main() -> int:
    violations = check()
    if violations:
        print("Wrapper modification detected:")
        for v in violations:
            print(f"  {v}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
