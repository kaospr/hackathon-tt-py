"""
TypeScript parser that extracts method bodies as raw strings.

Uses brace-counting to extract complete method bodies from TypeScript
class files. Handles various declaration patterns including access
modifiers, async, decorators, destructured parameters, and type
annotations.
"""
from __future__ import annotations

import re
from pathlib import Path


# Methods to skip -- they are either abstract (no body), too TS-specific,
# or infrastructure that the scaffold handles.
_SKIP_METHODS = {"constructor", "initialize"}

# Methods we want from each file
_ROAI_METHODS = {
    "calculateOverallPerformance",
    "getPerformanceCalculationType",
    "getSymbolMetrics",
}

_BASE_METHODS = {
    "computeSnapshot",
    "computeTransactionPoints",
    "getChartDateMap",
    "getPerformance",
    "getInvestments",
    "getInvestmentsByGroup",
}


def _find_method_start(content: str, pos: int) -> tuple[str, int, int] | None:
    """
    Starting from *pos*, find the next method declaration in a class body.

    Returns (method_name, declaration_start, pos_after_match) or None.

    Recognized patterns (all optional parts shown in brackets):
      [@Decorator]
      [public|protected|private] [static] [async] methodName ( ... ) [: ReturnType] {

    The regex captures the method name. The opening brace of the method body
    is located separately (it may be many lines after the declaration when
    there are destructured params or complex type annotations).
    """
    # Pattern matches a method declaration line.
    # We look for:
    #   optional decorator line(s) immediately preceding,
    #   optional access modifier, optional static, optional async,
    #   then an identifier followed by '(' (the params start).
    #
    # We do NOT try to match the full signature in one regex because
    # params can span many lines with destructured objects and type
    # annotations. Instead we just find the start and the method name,
    # then scan forward for the opening '{'.
    method_decl_re = re.compile(
        r"""
        ^[ \t]*                                      # leading whitespace
        (?:(?:@\w+)\s*\n[ \t]*)?                     # optional decorator line
        (?:public|protected|private)\s+               # required access modifier
        (?:static\s+)?                                # optional static
        (?:async\s+)?                                 # optional async
        (\w+)                                         # method name (capture group 1)
        \s*\(                                         # opening paren of params
        """,
        re.MULTILINE | re.VERBOSE,
    )

    m = method_decl_re.search(content, pos)
    if m is None:
        return None

    method_name = m.group(1)

    # Walk backwards from the match start to pick up a preceding decorator line
    decl_start = m.start()
    # Check the line above for a decorator like @LogPerformance
    line_start = content.rfind("\n", 0, decl_start)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    preceding_line = content[line_start:decl_start].strip()
    if preceding_line.startswith("@"):
        decl_start = line_start

    return method_name, decl_start, m.end()


def _is_abstract_declaration(content: str, pos: int) -> bool:
    """Return True if the line at *pos* is an abstract method (no body)."""
    # Find the start of this line
    line_start = content.rfind("\n", 0, pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    line_end = content.find("\n", pos)
    if line_end == -1:
        line_end = len(content)
    line = content[line_start:line_end]
    return "abstract" in line


def _find_opening_brace(content: str, pos: int) -> int | None:
    """Find the opening '{' of the method body, skipping params and return type."""
    i = _skip_param_list(content, pos)
    if i is None:
        return None
    return _scan_for_body_brace(content, i)


def _skip_param_list(content: str, pos: int) -> int | None:
    """Balance parentheses to skip past the parameter list."""
    depth = 1
    i = pos
    length = len(content)
    while i < length and depth > 0:
        ch = content[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch in ("'", '"', "`"):
            i = _skip_string(content, i)
            continue
        i += 1
    return i if i < length else None


def _scan_for_body_brace(content: str, i: int) -> int | None:
    """Scan past return type annotation to find the method body '{'."""
    length = len(content)
    state = [0, False]  # [brace_depth, found_colon]

    while i < length:
        ch = content[i]

        if ch in ("'", '"', "`"):
            i = _skip_string(content, i)
            continue

        i = _skip_comment(content, i)
        if i is None or i >= length:
            return None
        ch = content[i]

        result, i = _process_brace_char(content, i, ch, state)
        if result is not None:
            return result
    return None


def _process_brace_char(content, i, ch, state):
    """Process one character during body brace scanning. Returns (result, next_i)."""
    brace_depth, found_colon = state
    if ch == ";" and brace_depth == 0:
        return None, len(content)
    if ch == ":":
        state[1] = True
        found_colon = True
    if ch == "{":
        result = _handle_brace(content, i, brace_depth, found_colon)
        if isinstance(result, int) and result == i:
            return i, i  # Found body brace
        if isinstance(result, int):
            state[0] = result
            return None, i + 1
    elif ch == "}":
        state[0] = brace_depth - 1
        if state[0] < 0:
            return None, len(content)
    return None, i + 1


def _skip_comment(content: str, i: int) -> int | None:
    """Skip line or block comment at position i. Returns i if no comment."""
    length = len(content)
    if content[i] == "/" and i + 1 < length:
        if content[i + 1] == "/":
            nl = content.find("\n", i)
            return nl + 1 if nl != -1 else length
        if content[i + 1] == "*":
            end = content.find("*/", i + 2)
            return end + 2 if end != -1 else length
    return i


def _handle_brace(content: str, i: int, brace_depth: int, found_colon: bool):
    """Handle a '{' character. Returns i to signal body found, or new depth."""
    if brace_depth == 0 and found_colon:
        if _is_type_brace(content, i):
            return brace_depth + 1
        return i  # This IS the body brace
    if brace_depth > 0:
        return brace_depth + 1
    return i  # Body brace (no colon context)


def _is_type_brace(content: str, pos: int) -> bool:
    """
    Determine if the '{' at *pos* is a type annotation brace (not a method body).

    Heuristics:
    - Look at the trimmed content after '{'. Type annotation braces typically
      contain patterns like `[date: string]:` or `identifier:` as the first
      non-whitespace content.
    - Method bodies typically start with `const `, `let `, `return `, `for `,
      `if `, `this.`, `//`, a blank line then code, etc.
    """
    # Look at up to 200 chars after the brace
    snippet = content[pos + 1 : pos + 201].lstrip()

    # Type annotations: `[date: string]: boolean` or `key: Type`
    if re.match(r"\[", snippet):
        return True

    # Check what's BEFORE the '{' -- if it's `)` + optional whitespace, check
    # if this looks like a return type. Actually, let's check: if the line
    # containing this '{' has '):' before it on the same nesting level,
    # it's likely a type annotation in a method signature.
    # Simpler: check the content between the last ')' or '&' and this '{'
    lookback = content[max(0, pos - 100) : pos].rstrip()

    # If the lookback ends with a type annotation keyword or pattern, it's a type brace
    # e.g. `}: {` (continuation of destructured type) or `& AssetProfileIdentifier): SymbolMetrics {`
    # vs `...): Promise<PortfolioSnapshot> {` which is a body brace

    # Key insight: type annotation braces appear INSIDE the parameter list or
    # as part of the return type. If we see patterns like:
    #   `}: {`  -- type continuation in params
    #   `string]: boolean };` -- definitely type
    # For return type braces, they look like `): { [date: string]: true } {`
    # where the SECOND `{` is the body.

    # Simple and reliable: if the first meaningful content is a type pattern
    # (identifier followed by colon, or [identifier: type]), it's a type brace.
    if re.match(r"\w+\s*:", snippet) and not re.match(
        r"\w+\s*:\s*(new|this|const|let|var|return|if|for|while|switch|await|function)\b",
        snippet,
    ):
        # Looks like `key: Type` -- type annotation
        return True

    return False


def _skip_string(content: str, pos: int) -> int:
    """
    Skip a string literal starting at *pos*.
    Handles single-quoted, double-quoted, and template literals.
    Returns the index after the closing quote.
    """
    quote = content[pos]
    i = pos + 1
    length = len(content)

    if quote == "`":
        # Template literal -- need to handle ${...} expressions
        depth = 0
        while i < length:
            ch = content[i]
            if ch == "\\" and i + 1 < length:
                i += 2
                continue
            if ch == "`" and depth == 0:
                return i + 1
            if ch == "$" and i + 1 < length and content[i + 1] == "{":
                depth += 1
                i += 2
                continue
            if ch == "}" and depth > 0:
                depth -= 1
            i += 1
        return i

    # Single or double quoted string
    while i < length:
        ch = content[i]
        if ch == "\\" and i + 1 < length:
            i += 2
            continue
        if ch == quote:
            return i + 1
        i += 1
    return i


def _extract_method_body(content: str, brace_pos: int) -> int:
    """
    Given the position of the opening '{' of a method body, find
    the matching closing '}' using brace counting.

    Handles:
    - String literals (single, double, template with ${})
    - Line comments (//)
    - Block comments (/* */)
    - Nested objects/functions

    Returns the index of the closing '}'.
    """
    depth = 0
    i = brace_pos
    length = len(content)

    while i < length:
        ch = content[i]

        # Handle string literals
        if ch == "'" or ch == '"' or ch == "`":
            i = _skip_string(content, i)
            continue

        # Handle comments
        if ch == "/" and i + 1 < length:
            if content[i + 1] == "/":
                # Line comment -- skip to end of line
                nl = content.find("\n", i)
                i = nl + 1 if nl != -1 else length
                continue
            elif content[i + 1] == "*":
                # Block comment -- skip to */
                end = content.find("*/", i + 2)
                i = end + 2 if end != -1 else length
                continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i

        i += 1

    return length - 1  # Fallback: end of content


def parse_ts_file(path: Path) -> dict[str, str]:
    """
    Open a TypeScript file, find all method declarations in class bodies,
    and extract complete method bodies using brace-counting.

    Returns a dict mapping method_name -> full method source (including
    the declaration line).

    Skips abstract methods (no body), constructors, and the `initialize`
    method.
    """
    content = path.read_text(encoding="utf-8")
    methods: dict[str, str] = {}

    pos = 0
    while True:
        result = _find_method_start(content, pos)
        if result is None:
            break

        method_name, decl_start, after_paren_open = result

        # Skip methods we don't want
        if method_name in _SKIP_METHODS:
            pos = after_paren_open
            continue

        # Check if this is an abstract declaration
        if _is_abstract_declaration(content, decl_start):
            pos = after_paren_open
            continue

        # Find the opening brace of the method body
        body_brace = _find_opening_brace(content, after_paren_open)
        if body_brace is None:
            # No body (abstract or declaration-only)
            pos = after_paren_open
            continue

        # Find the closing brace
        closing_brace = _extract_method_body(content, body_brace)

        # Extract full method source: from declaration start to closing brace (inclusive)
        method_source = content[decl_start : closing_brace + 1]

        # Strip @LogPerformance decorator lines -- they're TS-specific
        method_source = re.sub(
            r"^[ \t]*@LogPerformance\s*\n", "", method_source, flags=re.MULTILINE
        )

        methods[method_name] = method_source

        # Continue scanning after this method
        pos = closing_brace + 1

    return methods


def extract_methods(roai_path: Path, base_path: Path) -> dict[str, str]:
    """
    Extract the required methods from both the ROAI and base calculator
    TypeScript files.

    Args:
        roai_path: Path to `roai/portfolio-calculator.ts`
        base_path: Path to `portfolio-calculator.ts`

    Returns a combined dict with these keys:
        From ROAI: calculateOverallPerformance, getPerformanceCalculationType,
                   getSymbolMetrics
        From base: computeSnapshot, computeTransactionPoints, getChartDateMap,
                   getPerformance, getInvestments, getInvestmentsByGroup
    """
    roai_methods = parse_ts_file(roai_path)
    base_methods = parse_ts_file(base_path)

    result: dict[str, str] = {}

    for name in _ROAI_METHODS:
        if name in roai_methods:
            result[name] = roai_methods[name]

    for name in _BASE_METHODS:
        if name in base_methods:
            result[name] = base_methods[name]

    return result
