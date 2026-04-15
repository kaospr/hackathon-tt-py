"""
Syntax transforms: clean up TypeScript syntax into Python equivalents.

Handles imports, decorators, keywords, type annotations, literals,
operators, and other syntactic differences. Does NOT handle indentation
or brace-based control flow (see control_flow.py).
"""
from __future__ import annotations

import re


def apply(source: str) -> str:
    """Apply all syntax transforms to *source* and return the result."""
    s = source

    # ------------------------------------------------------------------
    # 1. Remove import lines
    # ------------------------------------------------------------------
    # Handles: import ... from '...';  and  import { ... } from '...';
    # May span multiple lines when the import list is wrapped.
    s = re.sub(
        r"^import\s+(?:\{[^}]*\}|[^\n;]+)\s+from\s+['\"][^'\"]+['\"];?\s*$",
        "",
        s,
        flags=re.MULTILINE,
    )
    # Also handle multi-line imports like:
    #   import {
    #     Foo,
    #     Bar
    #   } from '...';
    s = re.sub(
        r"^import\s*\{[^}]*?\}\s*from\s*['\"][^'\"]+['\"];?\s*$",
        "",
        s,
        flags=re.MULTILINE | re.DOTALL,
    )
    # Catch any remaining bare import lines
    s = re.sub(r"^import\b[^;]*;?\s*$", "", s, flags=re.MULTILINE)

    # ------------------------------------------------------------------
    # 2. Remove decorators  (@LogPerformance, etc.)
    # ------------------------------------------------------------------
    s = re.sub(r"^\s*@\w+.*$", "", s, flags=re.MULTILINE)

    # ------------------------------------------------------------------
    # 3. Remove 'export' keyword
    # ------------------------------------------------------------------
    s = re.sub(r"\bexport\s+(class|function|const|let|enum|interface|type|abstract)\b",
               r"\1", s)

    # ------------------------------------------------------------------
    # 5. Remove standalone type / interface declarations (before var decls
    #    so we don't confuse them)
    # ------------------------------------------------------------------
    # type Foo = ...;
    s = re.sub(r"^\s*type\s+\w+\s*=[^;]*;\s*$", "", s, flags=re.MULTILINE)
    # interface blocks (may span multiple lines)
    s = _remove_interface_blocks(s)

    # ------------------------------------------------------------------
    # 4. Remove type annotations from variable declarations
    # ------------------------------------------------------------------
    # let/const/var  name: Type = ...  ->  name = ...
    # Also handles complex types like { [key: string]: Big }
    s = re.sub(
        r"\b(?:let|const|var)\s+(\w+)\s*:\s*(?:\{[^}]*\}|[^=;]+?)\s*=",
        r"\1 =",
        s,
    )
    # let/const/var  name = ...  (no type annotation)
    s = re.sub(r"\b(?:let|const|var)\s+(\w+)\s*=", r"\1 =", s)
    # let/const/var  name: Type;  (declaration without assignment)
    s = re.sub(r"\b(?:let|const|var)\s+(\w+)\s*:\s*[^=;]+;", r"\1 = None", s)
    # let/const/var  name;
    s = re.sub(r"\b(?:let|const|var)\s+(\w+)\s*;", r"\1 = None", s)

    # ------------------------------------------------------------------
    # 6. Remove async / await keywords
    # ------------------------------------------------------------------
    s = re.sub(r"\basync\s+", "", s)
    s = re.sub(r"\bawait\s+", "", s)

    # ------------------------------------------------------------------
    # 7. Remove access modifiers from declarations
    # ------------------------------------------------------------------
    s = re.sub(r"\b(public|private|protected)\s+", "", s)
    s = re.sub(r"\bstatic\s+", "", s)

    # ------------------------------------------------------------------
    # 8. Remove 'readonly'
    # ------------------------------------------------------------------
    s = re.sub(r"\breadonly\s+", "", s)

    # ------------------------------------------------------------------
    # 9. Remove 'new' keyword  (new Big(x) -> Big(x))
    # ------------------------------------------------------------------
    s = re.sub(r"\bnew\s+", "", s)

    # ------------------------------------------------------------------
    # 10. this. -> self.
    # ------------------------------------------------------------------
    s = re.sub(r"\bthis\.", "self.", s)

    # ------------------------------------------------------------------
    # 11. null / undefined -> None
    # ------------------------------------------------------------------
    s = re.sub(r"\bnull\b", "None", s)
    s = re.sub(r"\bundefined\b", "None", s)

    # ------------------------------------------------------------------
    # 12. Boolean literals
    # ------------------------------------------------------------------
    s = re.sub(r"\btrue\b", "True", s)
    s = re.sub(r"\bfalse\b", "False", s)

    # ------------------------------------------------------------------
    # 13. Strict equality
    # ------------------------------------------------------------------
    s = s.replace("===", "==")
    s = s.replace("!==", "!=")

    # ------------------------------------------------------------------
    # 14. Remove trailing semicolons (but not in strings or for-headers)
    # ------------------------------------------------------------------
    s = _remove_trailing_semicolons(s)

    # ------------------------------------------------------------------
    # 15. Number.EPSILON -> float epsilon
    # ------------------------------------------------------------------
    s = s.replace("Number.EPSILON", "2.220446049250313e-16")

    # ------------------------------------------------------------------
    # Clean up blank lines that pile up after removals
    # ------------------------------------------------------------------
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s


# ======================================================================
# Helpers
# ======================================================================

def _remove_interface_blocks(source: str) -> str:
    """Remove ``interface Foo { ... }`` blocks that may span many lines."""
    result: list[str] = []
    lines = source.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*interface\s+\w+", line):
            # Skip until we close the matching brace
            depth = line.count("{") - line.count("}")
            i += 1
            while i < len(lines) and depth > 0:
                depth += lines[i].count("{") - lines[i].count("}")
                i += 1
            # If the interface was a single line without braces, we already
            # consumed it.  Otherwise i now points past the closing brace.
            continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _remove_trailing_semicolons(source: str) -> str:
    """Remove semicolons that sit at the end of a statement line.

    Leaves semicolons inside ``for (...)`` headers alone.
    """
    out_lines: list[str] = []
    for line in source.split("\n"):
        stripped = line.rstrip()
        if stripped.endswith(";"):
            # Don't strip if this looks like a for-loop header
            if not re.match(r"^\s*for\s*\(", stripped):
                stripped = stripped[:-1]
        out_lines.append(stripped)
    return "\n".join(out_lines)
