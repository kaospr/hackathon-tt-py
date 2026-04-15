"""Expression transforms: optional chaining, nullish coalescing,
array methods, arrow functions, template literals, operators.
"""
from __future__ import annotations

import re


def _convert_template_literals(source: str) -> str:
    """Convert JS template literals `...${expr}...` to Python f-strings."""

    def replace_template(m: re.Match) -> str:
        content = m.group(1)
        # Convert ${expr} to {expr} for Python f-string
        content = re.sub(r'\$\{', '{', content)
        return f'f"{content}"'

    # Match backtick strings (may span multiple lines)
    source = re.sub(r'`([^`]*?)`', replace_template, source, flags=re.DOTALL)
    return source


def _convert_optional_chaining(source: str) -> str:
    """Convert optional chaining ?. to plain . access.

    Since the TS code guards with if-checks and many ?. usages appear
    alongside ?? (nullish coalescing) which provides defaults, simply
    stripping ?. to . is safe and pragmatic.
    """
    # ?.[key] bracket access: x?.[key] -> x[key]
    source = re.sub(r'\?\.\[', '[', source)
    # ?. property access: x?.y -> x.y
    source = re.sub(r'\?\.', '.', source)
    return source


def _convert_nullish_coalescing(source: str) -> str:
    r"""Convert nullish coalescing ?? to Python equivalent.

    x ?? y  ->  (x if x is not None else y)

    Process iteratively, replacing one ?? at a time (rightmost first
    for correct right-associativity).
    """

    def replace_nullish(m: re.Match) -> str:
        lhs = m.group(1).rstrip()
        rhs = m.group(2).lstrip()
        return f'({lhs} if {lhs} is not None else {rhs})'

    # Iteratively replace ?? from right to left
    max_iterations = 20
    for _ in range(max_iterations):
        new_source = re.sub(
            r'([^\n(,=?]+?)\s*\?\?\s*([^\n,;)?]+(?:\([^)]*\))?)',
            replace_nullish,
            source,
            count=1,
        )
        if new_source == source:
            break
        source = new_source

    return source


def _convert_array_methods(source: str) -> str:
    """Convert JS array/object methods to Python equivalents."""

    # .push(x) -> .append(x)
    source = re.sub(r'\.push\(', '.append(', source)

    # .at(-1) -> [-1], .at(0) -> [0]
    source = re.sub(r'\.at\((-?\d+)\)', r'[\1]', source)

    # .includes(x) -> x in arr
    # Handle: ['BUY', 'SELL'].includes(type) -> type in ['BUY', 'SELL']
    def replace_includes(m: re.Match) -> str:
        arr = m.group(1)
        val = m.group(2)
        return f'{val} in {arr}'

    # Array literal .includes()
    source = re.sub(
        r'(\[(?:[^\]]*)\])\.includes\(([^)]+)\)',
        replace_includes,
        source,
    )
    # Variable .includes()
    source = re.sub(
        r'(\w+(?:\.\w+)*)\.includes\(([^)]+)\)',
        replace_includes,
        source,
    )

    # .concat(other) -> arr + other
    source = re.sub(
        r'(\w+(?:\.\w+)*)\.concat\(([^)]+)\)',
        r'\1 + \2',
        source,
    )

    # .length -> len()
    # Handle: arr.length, self.chartDates.length, obj[key].length, etc.
    # Avoid matching when followed by = (assignment to .length)
    def replace_length(m: re.Match) -> str:
        obj = m.group(1)
        return f'len({obj})'

    # Match identifiers with optional dot-access, bracket-access chains
    source = re.sub(
        r'(\w+(?:(?:\.\w+)|(?:\[[^\]]*\]))*)\.length(?!\s*=)',
        replace_length,
        source,
    )

    # Object.keys(obj) -> list(obj.keys())
    source = re.sub(
        r'Object\.keys\(([^)]+)\)',
        r'list(\1.keys())',
        source,
    )

    # Object.entries(obj) -> list(obj.items())
    source = re.sub(
        r'Object\.entries\(([^)]+)\)',
        r'list(\1.items())',
        source,
    )

    # Object.values(obj) -> list(obj.values())
    source = re.sub(
        r'Object\.values\(([^)]+)\)',
        r'list(\1.values())',
        source,
    )

    # Array.from(Set(x)) -> list(set(x))  (new already removed by syntax.py)
    source = re.sub(
        r'Array\.from\(Set\(([^)]+)\)\)',
        r'list(set(\1))',
        source,
    )
    # Handle case where `new` was not yet removed
    source = re.sub(
        r'Array\.from\(new\s+Set\(([^)]+)\)\)',
        r'list(set(\1))',
        source,
    )

    return source


def _convert_arrow_functions(source: str) -> str:
    """Convert arrow functions to Python lambdas.

    Handles:
    - ({ field }) => { return expr; }  ->  lambda _item: expr (with field -> _item.field)
    - (x) => { return expr; }  ->  lambda x: expr
    - (x) => expression  ->  lambda x: expression
    """

    # Destructured single-var arrow: ({ field }) => expr
    # Shared replacer for both block body and expression body forms.
    def _destructured_arrow(m: re.Match) -> str:
        varname = m.group(1).strip()
        body = m.group(2).strip()
        if ',' not in varname:
            body = re.sub(
                r'\b' + re.escape(varname) + r'\b', f'_item.{varname}', body
            )
        return f'lambda _item: {body}'

    # Block body: ({ field }) => { return expr; }
    source = re.sub(
        r'\(\{\s*(\w+)\s*\}\)\s*=>\s*\{\s*return\s+(.+?);\s*\}',
        _destructured_arrow,
        source,
    )
    # Expression body: ({ field }) => expression
    source = re.sub(
        r'\(\{\s*(\w+)\s*\}\)\s*=>\s*(?!\{)([^\n,)]+)',
        _destructured_arrow,
        source,
    )

    # (param) => { return expr; }  ->  lambda param: expr
    source = re.sub(
        r'\((\w+)\)\s*=>\s*\{\s*return\s+(.+?);\s*\}',
        r'lambda \1: \2',
        source,
    )

    # (param1, param2) => { return expr; }  ->  lambda param1, param2: expr
    source = re.sub(
        r'\((\w+),\s*(\w+)\)\s*=>\s*\{\s*return\s+(.+?);\s*\}',
        r'lambda \1, \2: \3',
        source,
    )

    # (param) => expression  ->  lambda param: expression
    source = re.sub(
        r'\((\w+)\)\s*=>\s*(?!\{)([^\n,;)]+)',
        r'lambda \1: \2',
        source,
    )

    # bare param => expression (no parentheses, single param)
    source = re.sub(
        r'(?<![.\w])(\w+)\s*=>\s*(?!\{)([^\n,;)]+)',
        r'lambda \1: \2',
        source,
    )

    return source


def _convert_spread_operator(source: str) -> str:
    """Convert spread operator.

    { ...obj, key: value } -> {**obj, "key": value}
    [...arr] -> [*arr]
    """
    # Object spread: { ...expr
    source = re.sub(r'\{\s*\.\.\.(\w+)', r'{**\1', source)

    # Array spread: [...expr]
    source = re.sub(r'\[\s*\.\.\.(\w+(?:\.\w+)*)', r'[*\1', source)

    return source


def _convert_typeof_instanceof(source: str) -> str:
    """Convert typeof and instanceof operators."""

    # x instanceof Big -> isinstance(x, Big)
    source = re.sub(
        r'(\w+(?:\.\w+)*(?:\[.*?\])?)\s+instanceof\s+(\w+)',
        r'isinstance(\1, \2)',
        source,
    )

    # typeof x === 'string' -> isinstance(x, str)
    source = re.sub(
        r"typeof\s+(\w+)\s*===?\s*['\"]string['\"]",
        r'isinstance(\1, str)',
        source,
    )

    # typeof x === 'number' -> isinstance(x, (int, float))
    source = re.sub(
        r"typeof\s+(\w+)\s*===?\s*['\"]number['\"]",
        r'isinstance(\1, (int, float))',
        source,
    )

    # typeof x === 'undefined' -> x is None
    source = re.sub(
        r"typeof\s+(\w+)\s*===?\s*['\"]undefined['\"]",
        r'\1 is None',
        source,
    )

    # typeof x !== 'undefined' -> x is not None
    source = re.sub(
        r"typeof\s+(\w+)\s*!==?\s*['\"]undefined['\"]",
        r'\1 is not None',
        source,
    )

    return source


def _convert_string_methods(source: str) -> str:
    """Convert JS string methods to Python equivalents."""

    # .substring(start, end) -> [start:end]
    source = re.sub(
        r'\.substring\(([^,)]+),\s*([^)]+)\)',
        r'[\1:\2]',
        source,
    )

    # .substring(start) -> [start:]
    source = re.sub(
        r'\.substring\(([^)]+)\)',
        r'[\1:]',
        source,
    )

    # .sort((a, b) => a.localeCompare(b)) -> .sort()
    # (arrow functions may already be converted to lambdas at this point)
    source = re.sub(
        r'\.sort\(\s*lambda\s+\w+,\s*\w+:\s*\w+\.localeCompare\(\w+\)\s*\)',
        '.sort()',
        source,
    )
    # Also handle if arrow function wasn't converted yet
    source = re.sub(
        r'\.sort\(\s*\(\s*\w+\s*,\s*\w+\s*\)\s*=>\s*\w+\.localeCompare\(\w+\)\s*\)',
        '.sort()',
        source,
    )

    return source


def _convert_ternary_expressions(source: str) -> str:
    """Convert JS ternary expressions to Python conditional expressions.

    condition ? valueIfTrue : valueIfFalse
    ->
    valueIfTrue if condition else valueIfFalse
    """

    def replace_ternary(m: re.Match) -> str:
        cond = m.group(1).strip()
        true_val = m.group(2).strip()
        false_val = m.group(3).strip()
        return f'{true_val} if {cond} else {false_val}'

    # Iteratively replace simple (non-nested) ternary expressions
    max_iterations = 20
    for _ in range(max_iterations):
        new_source = re.sub(
            r'(?<!=)\s*([^?\n:=]+?)\s*\?\s*([^?\n:]+?)\s*:\s*([^?\n;,)]+)',
            replace_ternary,
            source,
            count=1,
        )
        if new_source == source:
            break
        source = new_source

    return source


def _convert_number_epsilon(source: str) -> str:
    """Convert Number.EPSILON to Python equivalent."""
    source = re.sub(r'Number\.EPSILON', 'float_info.epsilon', source)
    return source


def _convert_new_date(source: str) -> str:
    """Convert new Date() and new Date(str) to Python equivalents.

    Note: `new` keyword may already be removed by syntax.py.
    """
    # Date() with no args (with or without `new`) -> datetime.now()
    source = re.sub(r'\b(?:new\s+)?Date\(\)', 'datetime.now()', source)

    # Date(expr) (with or without `new`) -> parse_date(expr)
    source = re.sub(r'\b(?:new\s+)?Date\(([^)]+)\)', r'parse_date(\1)', source)

    # .getTime() -> .timestamp()
    source = re.sub(r'\.getTime\(\)', '.timestamp()', source)

    return source


def _convert_equality_operators(source: str) -> str:
    """Convert JS strict equality to Python equality."""
    # === -> ==
    source = re.sub(r'===', '==', source)
    # !== -> !=
    source = re.sub(r'!==', '!=', source)
    return source


def _convert_logical_operators(source: str) -> str:
    """Convert JS logical operators to Python."""
    # && -> and
    source = re.sub(r'\s*&&\s*', ' and ', source)
    # || -> or
    source = re.sub(r'\s*\|\|\s*', ' or ', source)
    # ! (logical not) -> not  (but not != or !==)
    source = re.sub(r'(?<![!=])!(?!=)(?=\w)', 'not ', source)
    return source


def _convert_type_casts(source: str) -> str:
    """Remove TypeScript type casts and assertions.

    expr as Type -> expr
    """
    # `as TypeName` or `as TypeName[]`
    source = re.sub(r'\s+as\s+\w+(?:\[\])?(?:\s*\[\s*\])?', '', source)

    # `as { key: Type }` type casts with braces
    source = re.sub(r'\s+as\s+\{[^}]+\}', '', source)

    return source


def _convert_semicolons(source: str) -> str:
    """Remove trailing semicolons from statements."""
    source = re.sub(r';(\s*)$', r'\1', source, flags=re.MULTILINE)
    source = re.sub(r';\s*\n', '\n', source)
    return source


def apply(source: str) -> str:
    """Apply expression transforms to source."""

    # Order matters: some transforms depend on others

    # 1. Template literals (before other string changes)
    source = _convert_template_literals(source)

    # 2. Optional chaining (before nullish coalescing, since x?.y ?? z is common)
    source = _convert_optional_chaining(source)

    # 3. Type casts (remove before other processing)
    source = _convert_type_casts(source)

    # 4. Equality operators
    source = _convert_equality_operators(source)

    # 5. Logical operators
    source = _convert_logical_operators(source)

    # 6. typeof/instanceof
    source = _convert_typeof_instanceof(source)

    # 7. Number.EPSILON
    source = _convert_number_epsilon(source)

    # 8. new Date() conversions
    source = _convert_new_date(source)

    # 9. Arrow functions (before array methods, since filter/map take arrow fns)
    source = _convert_arrow_functions(source)

    # 10. Array/Object methods
    source = _convert_array_methods(source)

    # 11. String methods
    source = _convert_string_methods(source)

    # 12. Spread operator
    source = _convert_spread_operator(source)

    # 13. Ternary expressions
    source = _convert_ternary_expressions(source)

    # 14. Nullish coalescing (after optional chaining and ternary)
    source = _convert_nullish_coalescing(source)

    # 15. Semicolons
    source = _convert_semicolons(source)

    return source
