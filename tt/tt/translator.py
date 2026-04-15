"""
TypeScript to Python translator.

Orchestrates the translation pipeline:
1. Parse TS source files to extract method bodies
2. Apply regex-based transforms to convert TS syntax to Python
3. Assemble translated methods into the final Python calculator file
"""
from __future__ import annotations

from pathlib import Path

from .ts_parser import extract_methods
from .transforms import apply_all
from .assembler import assemble


def translate_methods(methods: dict[str, str]) -> dict[str, str]:
    """Apply the transform pipeline to each extracted method body."""
    translated = {}
    for name, body in methods.items():
        translated[name] = apply_all(body)
    return translated


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Run the full translation pipeline."""
    # Source TypeScript files
    roai_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "roai" / "portfolio-calculator.ts"
    )
    base_ts = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "portfolio-calculator.ts"
    )

    # Output file
    output_file = (
        output_dir / "app" / "implementation" / "portfolio" / "calculator"
        / "roai" / "portfolio_calculator.py"
    )

    if not roai_ts.exists():
        print(f"Warning: ROAI TypeScript source not found: {roai_ts}")
        return

    if not base_ts.exists():
        print(f"Warning: Base TypeScript source not found: {base_ts}")
        return

    print(f"Parsing TypeScript sources...")
    methods = extract_methods(roai_ts, base_ts)

    print(f"Applying transforms to {len(methods)} methods...")
    translated = translate_methods(methods)

    print(f"Assembling output...")
    output_content = assemble(translated)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output_content, encoding="utf-8")
    print(f"  Translated -> {output_file}")
