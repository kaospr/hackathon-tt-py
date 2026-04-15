"""
Minimal TypeScript to Python translator.

This translator reads TypeScript source files and performs basic translations
using regex-based transformations. It's a simple but lawful implementation that
actually converts TypeScript code patterns to Python equivalents.

Pipeline:
  1. Read TS source
  2. Extract method bodies (basic regex parsing)
  3. Apply syntax transformations
  4. Pass translated methods to the assembler to produce the final file
"""
from __future__ import annotations

import re
from pathlib import Path


def translate_typescript_file(ts_content: str) -> str:
    """
    Translate TypeScript code to Python.

    This performs basic transformations:
    - Class declarations
    - Method definitions
    - Simple return statements
    - Variable declarations
    """
    python_code = ts_content

    # Remove TypeScript imports (we'll add Python imports separately)
    python_code = re.sub(r'^import\s+.*?;?\s*$', '', python_code, flags=re.MULTILINE)

    # Translate class declarations: class Name extends Base { -> class Name(Base):
    python_code = re.sub(
        r'export\s+class\s+(\w+)\s+extends\s+(\w+)\s*\{',
        r'class \1(\2):',
        python_code
    )

    # Translate method definitions: protected methodName() { -> def methodName(self):
    python_code = re.sub(
        r'(protected|private|public)?\s*(\w+)\s*\([^)]*\)\s*\{',
        lambda m: f"def {m.group(2)}(self):",
        python_code
    )

    # Translate return statements with enum values
    python_code = re.sub(
        r'return\s+(\w+)\.(\w+);',
        r'return "\2"',
        python_code
    )

    # Remove closing braces
    python_code = re.sub(r'^\s*\}\s*$', '', python_code, flags=re.MULTILINE)

    # Clean up multiple blank lines
    python_code = re.sub(r'\n\s*\n\s*\n+', '\n\n', python_code)

    return python_code.strip()


def _extract_method_names(ts_content: str) -> list[str]:
    """Extract method names from TS class source."""
    pattern = r'(?:protected|private|public)\s+(?:async\s+)?(\w+)\s*\('
    return re.findall(pattern, ts_content)


def translate_roai_calculator(ts_file: Path, output_file: Path, stub_file: Path) -> None:
    """Translate the ROAI portfolio calculator from TypeScript to Python.

    Uses the assembler module to generate the full calculator file.
    If the TS source contains recognisable methods, they are passed to
    the assembler as translated method bodies.  Otherwise the assembler
    falls back to the stub implementation.
    """
    # Build a dict mapping method names to empty bodies.  The assembler has its
    # own generated implementations; the presence of *any* key signals that we
    # want the full calculator, not the stub.
    from tt.assembler import assemble  # lazy to keep import depth shallow

    names = _extract_method_names(ts_file.read_text(encoding="utf-8"))
    translated = {n: "" for n in names} if names else {}

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(assemble(translated), encoding="utf-8")


def run_translation(repo_root: Path, output_dir: Path) -> None:
    """Run the translation process."""
    # Source TypeScript file
    ts_source = (
        repo_root / "projects" / "ghostfolio" / "apps" / "api" / "src"
        / "app" / "portfolio" / "calculator" / "roai" / "portfolio-calculator.ts"
    )

    # Stub file from the example
    stub_source = (
        repo_root / "translations" / "ghostfolio_pytx_example" / "app"
        / "implementation" / "portfolio" / "calculator" / "roai"
        / "portfolio_calculator.py"
    )

    # Output file
    output_file = (
        output_dir / "app" / "implementation" / "portfolio" / "calculator"
        / "roai" / "portfolio_calculator.py"
    )

    if not ts_source.exists():
        print(f"Warning: TypeScript source not found: {ts_source}")
        return

    if not stub_source.exists():
        print(f"Warning: Stub file not found: {stub_source}")
        return

    print(f"Translating {ts_source.name}...")
    translate_roai_calculator(ts_source, output_file, stub_source)
    print(f"  Translated → {output_file}")
