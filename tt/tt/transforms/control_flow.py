"""
Control-flow transforms: convert TypeScript block structures to Python.

Handles for-loops, if/else, ternary expressions, comments, and the
conversion from brace-delimited blocks to indentation-based blocks.
"""
from __future__ import annotations

import re

# Regex matching an assignment boundary: ``prefix = rest`` where ``=`` is
# a plain assignment (not ``==``, ``!=``, ``>=``, ``<=``).
_ASSIGN_BOUNDARY_RE = re.compile(r"^(.*?(?<![=!<>])=(?!=)\s*)(.*?)$", re.DOTALL)


def _process_lines(text: str, fn) -> str:
    """Split *text* into lines, apply *fn* to each, and rejoin."""
    return "\n".join(fn(line) for line in text.split("\n"))


def apply(source: str) -> str:
    """Apply all control-flow transforms and return the result."""
    s = source

    # Order matters — comments first (so we don't misparse ``//`` inside
    # code), then ternaries, then control statements, then braces.

    # ------------------------------------------------------------------
    # 6 & 7. Comments  (block and line)
    # ------------------------------------------------------------------
    s = _convert_block_comments(s)
    s = _convert_line_comments(s)

    # ------------------------------------------------------------------
    # 5. Ternary expressions  (must come before brace removal so that
    #    multi-line ternaries still have their original structure)
    # ------------------------------------------------------------------
    s = _convert_multi_line_ternaries(s)
    s = _convert_single_line_ternaries(s)

    # ------------------------------------------------------------------
    # 1. for-of loops
    # ------------------------------------------------------------------
    s = _convert_for_of(s)

    # ------------------------------------------------------------------
    # 2. C-style for loops
    # ------------------------------------------------------------------
    s = _convert_c_style_for(s)

    # ------------------------------------------------------------------
    # 3. if / else if / else
    # ------------------------------------------------------------------
    s = _convert_if_else(s)

    # ------------------------------------------------------------------
    # 4. Remove standalone closing braces (LAST)
    # ------------------------------------------------------------------
    s = _remove_closing_braces(s)

    # Clean up excessive blank lines
    s = re.sub(r"\n{3,}", "\n\n", s)

    return s


# ======================================================================
# for-of loops
# ======================================================================

def _convert_for_of(source: str) -> str:
    """``for (const x of arr) {`` -> ``for x in arr:``"""
    # Simple variable binding
    s = re.sub(
        r"\bfor\s*\(\s*(?:const|let|var)\s+(\w+)\s+of\s+(.+?)\)\s*\{",
        r"for \1 in \2:",
        source,
    )
    # Destructured binding: for (const { a, b } of arr) {
    # We turn it into: for _item in arr:  with unpacking on the next line
    # Actually, a simpler approach: keep the destructured names inline
    # for ({ a, b } of arr) -> for _item in arr:\n  a = _item['a']; b = ...
    # But that's very complex.  A pragmatic approach: convert to
    # ``for _item in arr:`` and let a later pass handle unpacking.
    # For now, just handle simple destructuring by keeping variable names.
    def _destr_for_of(m: re.Match) -> str:
        vars_str = m.group(1)  # e.g. " a, b "
        iterable = m.group(2)
        # Clean up the variable names
        var_names = [v.strip() for v in vars_str.split(",") if v.strip()]
        if len(var_names) == 1:
            return f"for {var_names[0]} in {iterable}:"
        # Multiple destructured names — Python doesn't support dict
        # destructuring in for-loops, so we use a placeholder.
        return f"for _item in {iterable}:"
    s = re.sub(
        r"\bfor\s*\(\s*(?:const|let|var)\s+\{\s*([^}]+)\s*\}\s+of\s+(.+?)\)\s*\{",
        _destr_for_of,
        s,
    )
    return s


# ======================================================================
# C-style for loops
# ======================================================================

def _convert_c_style_for(source: str) -> str:
    """Convert common C-style for patterns to Python range() loops."""
    return _process_lines(source, _try_convert_c_for_line)


def _try_convert_c_for_line(line: str) -> str:
    """Try to convert a single line containing a C-style for loop."""
    m = _match_c_for(line)
    if not m:
        return line
    return _build_range_loop(m) or line


_C_FOR_RE = re.compile(
    r"^(\s*)for\s*\(\s*"
    r"(?:let|var|const)?\s*(\w+)\s*=\s*([^;]+);\s*"
    r"(\w+)\s*([<>=!]+)\s*([^;]+);\s*"
    r"(\w+)\s*([+\-*/]=?)\s*(\d+)"
    r"\s*\)\s*\{"
)


def _match_c_for(line: str) -> re.Match | None:
    """Match and validate a C-style for-loop line."""
    m = _C_FOR_RE.match(line)
    if not m:
        return None
    if not (m.group(2) == m.group(4) == m.group(7)):
        return None
    return m


def _range_up_by_one(indent, var, init_val, end, **_):
    """``for i = 0; i < N; i += 1`` -> ``for i in range(N):``"""
    start = "" if init_val == "0" else f"{init_val}, "
    return f"{indent}for {var} in range({start}{end}):"


def _range_down_by_one(indent, var, init_val, cond_val, **_):
    """``for i = N; i >= 0; i -= 1`` -> ``for i in range(N, -1, -1):``"""
    start = _length_expr(init_val)
    stop = "-1" if cond_val == "0" else f"{_length_expr(cond_val)} - 1"
    return f"{indent}for {var} in range({start}, {stop}, -1):"


def _range_up_by_step(indent, var, init_val, end, step, **_):
    """``for i = 0; i < N; i += S`` -> ``for i in range(0, N, S):``"""
    start_arg = "" if init_val == "0" else f"{init_val}, "
    return f"{indent}for {var} in range({start_arg}{end}, {step}):"


# Maps (cond_op, upd_op, step_is_one) -> builder function
_RANGE_BUILDERS: dict[tuple[str, str, bool], callable] = {
    ("<", "+=", True): _range_up_by_one,
    (">=", "-=", True): _range_down_by_one,
    ("<", "+=", False): _range_up_by_step,
}


def _build_range_loop(m: re.Match) -> str | None:
    """Build a Python range() loop from a C-style for regex match."""
    indent, var = m.group(1), m.group(2)
    init_val, cond_op = m.group(3).strip(), m.group(5)
    cond_val, upd_op, step = m.group(6).strip(), m.group(8), m.group(9)
    end = _length_expr(cond_val)

    key = (cond_op, upd_op, step == "1")
    builder = _RANGE_BUILDERS.get(key)
    if builder is None:
        return None
    return builder(
        indent=indent, var=var, init_val=init_val,
        end=end, cond_val=cond_val, step=step,
    )


def _length_expr(expr: str) -> str:
    """Convert ``foo.length`` to ``len(foo)`` in range expressions."""
    # arr.length or self.chartDates.length -> len(...)
    m = re.match(r"^(\w+(?:\.\w+)*)\.length$", expr)
    if m:
        return f"len({m.group(1)})"
    # arr.length - N  ->  len(arr) - N
    m = re.match(r"^(\w+(?:\.\w+)*)\.length\s*-\s*(\d+)$", expr)
    if m:
        return f"len({m.group(1)}) - {m.group(2)}"
    return expr


# ======================================================================
# if / else if / else
# ======================================================================

def _convert_if_else(source: str) -> str:
    """Convert if/else-if/else blocks."""
    s = source

    # } else if (condition) {  ->  elif condition:
    s = re.sub(
        r"\}\s*else\s+if\s*\((.+?)\)\s*\{",
        r"elif \1:",
        s,
    )

    # } else {  ->  else:
    s = re.sub(
        r"\}\s*else\s*\{",
        "else:",
        s,
    )

    # if (condition) {  ->  if condition:
    s = re.sub(
        r"\bif\s*\((.+?)\)\s*\{",
        r"if \1:",
        s,
    )

    # Handle multi-line if conditions:
    # if (
    #   condition
    # ) {
    def _multiline_if(m: re.Match) -> str:
        keyword = m.group(1)  # "if" or "elif" or "} else if"
        condition = m.group(2).strip()
        # Clean up: collapse internal newlines to a single space
        condition = re.sub(r"\s*\n\s*", " ", condition)
        if "else if" in keyword:
            return f"elif {condition}:"
        return f"if {condition}:"

    s = re.sub(
        r"(if|}\s*else\s+if)\s*\(\s*\n([\s\S]*?)\n\s*\)\s*\{",
        _multiline_if,
        s,
    )

    return s


# ======================================================================
# Closing braces
# ======================================================================

def _remove_closing_braces(source: str) -> str:
    """Remove lines that consist only of a closing brace (block-closing).

    Only removes lines where the sole content is ``}``, optionally followed
    by ``;``.  Since control-flow opening braces have already been stripped
    (``if (...) {`` became ``if ...:``) by the time this runs, remaining
    standalone ``}`` are block-closing braces.  Object literal braces that
    appear *inline* (e.g. ``return { a: 1 }``) are unaffected because
    they share a line with other code.
    """
    return "\n".join(
        line for line in source.split("\n")
        if line.strip() not in ("}", "};")
    )


# ======================================================================
# Ternary expressions
# ======================================================================

def _convert_single_line_ternaries(source: str) -> str:
    """Convert ``cond ? valA : valB`` to ``valA if cond else valB``.

    Only handles ternaries that fit on a single logical line.
    """
    return _process_lines(source, _ternary_line)


def _ternary_line(line: str) -> str:
    """Convert ternaries in a single line.  Handles nested ternaries."""
    # Skip comment lines
    stripped = line.lstrip()
    if stripped.startswith("#") or stripped.startswith("//"):
        return line

    # Match:  <condition> ? <true_val> : <false_val>
    # We need to be careful about ? used in optional chaining (?.) and
    # nullish coalescing (??)
    # Strategy: find the first non-optional-chaining ? and work from there
    return _convert_ternaries_in_text(line)


def _is_ternary_qmark(text: str, pos: int) -> bool:
    """Return True if the ``?`` at *pos* looks like a ternary operator."""
    if pos + 1 < len(text) and text[pos + 1] in (".", "?"):
        return False  # optional-chaining (?.) or nullish coalescing (??)
    return pos > 0 and text[pos + 1:pos + 2] in (" ", "\t", "\n", "")


def _convert_ternaries_in_text(text: str) -> str:
    """Recursively convert ternary expressions in a piece of text."""
    idx = 0
    while idx < len(text):
        qmark = text.find("?", idx)
        if qmark == -1:
            break
        if _is_ternary_qmark(text, qmark):
            converted = _try_parse_ternary(text, qmark)
            if converted is not None:
                return converted
        idx = qmark + (2 if qmark + 1 < len(text) and text[qmark + 1] in (".", "?") else 1)
    return text


def _try_parse_ternary(text: str, qmark_pos: int) -> str | None:
    """Try to parse a ternary at the given ``?`` position.

    Returns the converted string or None if this isn't a valid ternary.
    """
    # Find the condition (everything before the ?)
    # We need to find where the condition starts.  It's typically after
    # an = or at the start of an expression context.
    # For a simple approach: scan back to find the start of the expression.
    condition_end = qmark_pos
    # The condition is everything from the last assignment/statement boundary
    # to the ?
    before = text[:condition_end].rstrip()

    # Find the colon that matches this ternary (accounting for nesting)
    colon_pos = _find_matching_colon(text, qmark_pos + 1)
    if colon_pos is None:
        return None

    true_val = text[qmark_pos + 1:colon_pos].strip()
    false_val_and_rest = text[colon_pos + 1:]

    # The false value extends to the end of the expression.
    # For simple cases this is until end of line or a semicolon.
    false_val = false_val_and_rest.strip()

    # Recursively convert any nested ternaries in the true/false branches
    true_val = _convert_ternaries_in_text(true_val)
    false_val = _convert_ternaries_in_text(false_val)

    # Reconstruct: condition stays with 'before', and we rewrite the ternary
    # as: true_val if condition else false_val
    # But we need to extract just the condition part from 'before'
    # Strategy: the condition is the rightmost expression in 'before'
    # after the last = sign (or the whole 'before' if no =)
    assign_match = _ASSIGN_BOUNDARY_RE.search(before)
    if assign_match and assign_match.group(2).strip():
        prefix = assign_match.group(1)
        condition = assign_match.group(2).strip()
    else:
        prefix = ""
        condition = before.strip()

    return f"{prefix}{true_val} if {condition} else {false_val}"


_BRACKET_DELTAS = {"(": (1, 0), ")": (-1, 0), "[": (0, 1), "]": (0, -1)}


def _is_ternary_question(text: str, i: int) -> bool:
    """Return True if ``?`` at position *i* is a ternary (not ``?.`` or ``??``)."""
    return i + 1 < len(text) and text[i + 1] not in (".", "?")


def _find_matching_colon(text: str, start: int) -> int | None:
    """Find the ``:`` that matches the ternary ``?``, accounting for nesting."""
    depth = paren = bracket = 0
    for i in range(start, len(text)):
        ch = text[i]
        deltas = _BRACKET_DELTAS.get(ch)
        if deltas:
            paren += deltas[0]
            bracket += deltas[1]
            continue
        if paren != 0 or bracket != 0:
            continue
        if ch == "?" and _is_ternary_question(text, i):
            depth += 1
        elif ch == ":" and depth == 0:
            return i
        elif ch == ":":
            depth -= 1
    return None


def _convert_multi_line_ternaries(source: str) -> str:
    """Convert multi-line ternary expressions.

    Handles patterns like::

        const x = condition
          ? valueA
          : valueB;

    And also patterns where the true/false values span multiple lines::

        const x = condition
          ? a
              .b()
              .c()
          : d;

    And split-line assignments::

        const x =
          condition
            ? valueA
            : valueB;

    Becomes ``x = valueA if condition else valueB``
    """
    # Keep applying until stable (nested ternaries need multiple passes)
    prev = None
    while prev != source:
        prev = source
        source = _multiline_ternary_pass(source)
    return source


def _try_ternary_at(lines: list[str], i: int) -> tuple[str | None, int]:
    """Try to convert a multi-line ternary starting at line *i*.

    Returns ``(converted_line, lines_consumed)`` on success, or
    ``(None, 0)`` if no ternary pattern was found.
    """
    if i + 1 >= len(lines):
        return None, 0
    if lines[i + 1].lstrip().startswith("? "):
        return _parse_multiline_ternary(lines, i)
    if i + 2 < len(lines) and lines[i + 2].lstrip().startswith("? "):
        return _parse_multiline_ternary_split(lines, i)
    return None, 0


def _multiline_ternary_pass(source: str) -> str:
    """One pass of multi-line ternary conversion."""
    lines = source.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        converted, consumed = _try_ternary_at(lines, i)
        if converted is not None:
            result.append(converted)
            i += consumed
        else:
            result.append(lines[i])
            i += 1
    return "\n".join(result)


def _collect_continuation_lines(
    lines: list[str], i: int, base_indent: int, *, allow_nested: bool,
) -> tuple[list[str], int]:
    """Collect continuation lines for a ternary branch value.

    Returns the collected stripped parts and the updated line index.
    When *allow_nested* is True, nested ternary markers (``?`` / ``:``)
    at deeper indent are included (used for the false-value branch).
    """
    parts: list[str] = []
    while i < len(lines):
        stripped = lines[i].lstrip()
        line_indent = len(lines[i]) - len(stripped)
        is_marker = stripped.startswith(("? ", ": "))
        # Stop at markers on the same or shallower indent level
        if is_marker and line_indent <= base_indent:
            break
        # Include deeper-indent content (markers only when allow_nested)
        if line_indent > base_indent and (stripped and (not is_marker or allow_nested)):
            parts.append(stripped)
            i += 1
            continue
        break
    return parts, i


def _parse_multiline_ternary(lines: list[str], start: int) -> tuple[str | None, int]:
    """Parse a multi-line ternary: ``<prefix> = <cond> \\n ? <T> \\n : <F>``."""
    condition_line = lines[start]
    i = start + 1

    if i >= len(lines) or not lines[i].lstrip().startswith("? "):
        return None, 1

    true_val, false_val, i = _collect_ternary_branches(lines, i)
    if true_val is None:
        return None, 1

    prefix, cond = _split_condition_line(condition_line)
    return f"{prefix}{true_val} if {cond} else {false_val}", i - start


def _collect_ternary_branches(lines, i):
    """Collect true and false branches of a multi-line ternary starting at ?-line."""
    q_indent = len(lines[i]) - len(lines[i].lstrip())
    true_parts = [lines[i].lstrip()[2:].strip()]
    i += 1
    collected, i = _collect_continuation_lines(lines, i, q_indent, allow_nested=False)
    true_parts.extend(collected)

    if i >= len(lines) or not lines[i].lstrip().startswith(": "):
        return None, None, i

    c_indent = len(lines[i]) - len(lines[i].lstrip())
    false_parts = [lines[i].lstrip()[2:].strip()]
    i += 1
    collected, i = _collect_continuation_lines(lines, i, c_indent, allow_nested=True)
    false_parts.extend(collected)

    true_val = " ".join(true_parts)
    false_val = " ".join(false_parts)
    if "? " in false_val:
        false_val = _convert_ternaries_in_text(false_val)
    return true_val, false_val, i


def _split_condition_line(condition_line):
    """Extract prefix and condition from the assignment/condition line."""
    cond_line = condition_line.rstrip()
    assign_match = _ASSIGN_BOUNDARY_RE.match(cond_line)
    if assign_match and assign_match.group(2).strip():
        return assign_match.group(1), assign_match.group(2).strip()
    return re.match(r"^(\s*)", cond_line).group(1), cond_line.strip()


def _parse_multiline_ternary_split(lines: list[str], start: int) -> tuple[str | None, int]:
    """Parse a multi-line ternary where the assignment, condition, and ``?``
    are all on separate lines.

    Pattern::

        <prefix> =
          <condition>
            ? <trueVal>
            : <falseVal>
    """
    assign_line = lines[start]
    # The assignment line should end with = (possibly after stripping)
    if not assign_line.rstrip().endswith("="):
        return None, 1

    condition_line = lines[start + 1]
    i = start + 2

    if i >= len(lines):
        return None, 1
    if not lines[i].lstrip().startswith("? "):
        return None, 1

    # Re-use the main parser from the condition line onward
    result, consumed = _parse_multiline_ternary(lines, start + 1)
    if result is None:
        return None, 1

    # The result has the condition line as prefix; we need to prepend the
    # assignment prefix instead
    prefix = assign_line.rstrip()  # "    someVar ="
    # result starts with the condition line's indent; replace it
    result_stripped = result.lstrip()
    indent = re.match(r"^(\s*)", assign_line).group(1)
    return f"{prefix} {result_stripped}", consumed + 1


# ======================================================================
# Comments
# ======================================================================

def _convert_block_comments(source: str) -> str:
    r"""Convert ``/* ... */`` to ``# ...`` lines."""
    # Match the entire line(s) containing the block comment, including
    # leading whitespace on the opening line, so the replacement doesn't
    # double the indentation.
    def _repl(m: re.Match) -> str:
        indent = m.group(1)
        body = m.group(2)
        result_lines = [
            f"{indent}# {cleaned}"
            for line in body.split("\n")
            if (cleaned := re.sub(r"^\s*\*\s?", "", line).strip())
        ]
        return "\n".join(result_lines) if result_lines else ""

    return re.sub(r"^([ \t]*)/\*(.*?)\*/", _repl, source,
                  flags=re.DOTALL | re.MULTILINE)


def _convert_line_comments(source: str) -> str:
    """Convert ``// comment`` to ``# comment``."""
    return re.sub(r"//(.*)$", r"#\1", source, flags=re.MULTILINE)
