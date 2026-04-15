"""Library-specific transforms: date-fns, lodash, console.log, Logger."""
from __future__ import annotations

import re

# Simple camelCase -> snake_case function renames.  Each entry maps
# a TypeScript function name to its Python equivalent.  The rename is
# applied as ``\bOLD\(`` -> ``NEW(``.
_SIMPLE_RENAMES: list[tuple[str, str]] = [
    # date-fns
    ("differenceInDays", "difference_in_days"),
    ("isBefore", "is_before"),
    ("isAfter", "is_after"),
    ("addMilliseconds", "add_milliseconds"),
    ("startOfYear", "start_of_year"),
    ("endOfYear", "end_of_year"),
    ("startOfDay", "start_of_day"),
    ("endOfDay", "end_of_day"),
    ("startOfMonth", "start_of_month"),
    ("subDays", "sub_days"),
    ("subYears", "sub_years"),
    ("isThisYear", "is_this_year"),
    ("isWithinInterval", "is_within_interval"),
    ("parseDate", "parse_date"),
    ("resetHours", "reset_hours"),
    ("getIntervalFromDateRange", "get_interval_from_date_range"),
    # lodash / helpers
    ("cloneDeep", "clone_deep"),
    ("sortBy", "sort_by"),
    ("uniqBy", "uniq_by"),
    ("isNumber", "is_number"),
    ("getSum", "get_sum"),
    ("getFactor", "get_factor"),
]


def _apply_simple_renames(source: str) -> str:
    """Apply all simple function renames from the table above."""
    for old, new in _SIMPLE_RENAMES:
        source = re.sub(rf'\b{old}\(', f'{new}(', source)
    return source


def _remove_logging_lines(source: str) -> str:
    """Remove console.log, Logger.warn, Logger.debug lines entirely."""
    # Remove lines/blocks for each logging call pattern
    for call in (r'console\.log', r'Logger\.warn', r'Logger\.debug'):
        # Single-line calls
        source = re.sub(
            rf'^[^\n]*{call}\([^)]*\)[^\n]*\n?', '', source,
            flags=re.MULTILINE,
        )
        # Multi-line calls (content spanning lines)
        source = re.sub(
            rf'^\s*{call}\(.*?\);\s*\n?', '', source,
            flags=re.MULTILINE | re.DOTALL,
        )

    # Remove ENABLE_LOGGING guard blocks containing console.log
    source = re.sub(
        r'if\s*\(\s*PortfolioCalculator\.ENABLE_LOGGING\s*\)\s*\{[^}]*console\.log[^}]*\}',
        '',
        source,
        flags=re.DOTALL,
    )

    return source


def _convert_enable_logging(source: str) -> str:
    """Convert PortfolioCalculator.ENABLE_LOGGING to False."""
    source = re.sub(
        r'PortfolioCalculator\.ENABLE_LOGGING',
        'False',
        source,
    )
    return source


def _convert_interval_call(source: str, ts_name: str, py_name: str) -> str:
    """Convert ``tsName({ end, start }, { step? })`` to ``py_name(start, end[, step])``."""
    # Both property orderings: {end, start} and {start, end}, with optional step
    _PROP = r'(?::\s*(\w+))?'
    for first, second, start_grp, end_grp in [
        ('end', 'start', 2, 1),
        ('start', 'end', 1, 2),
    ]:
        # With step argument
        pat_step = (
            rf'\b{ts_name}\(\s*\{{\s*{first}\s*{_PROP}\s*,\s*{second}\s*{_PROP}\s*\}}'
            rf'\s*,\s*\{{\s*step\s*{_PROP}\s*\}}\s*\)'
        )
        source = re.sub(
            pat_step,
            lambda m, sg=start_grp, eg=end_grp: f'{py_name}({m.group(sg) or first}, {m.group(eg) or second}, {m.group(3) or "step"})',
            source,
        )
        # Without step argument
        pat_no_step = (
            rf'\b{ts_name}\(\s*\{{\s*{first}\s*{_PROP}\s*,\s*{second}\s*{_PROP}\s*\}}\s*\)'
        )
        source = re.sub(
            pat_no_step,
            lambda m, sg=start_grp, eg=end_grp: f'{py_name}({m.group(sg) or first}, {m.group(eg) or second})',
            source,
        )
    return source


def _convert_date_fns(source: str) -> str:
    """Convert date-fns function calls to Python helper equivalents."""

    # format(date, DATE_FORMAT) -> format_date(date)
    # format(date, 'yyyy-MM-dd') -> format_date(date)
    # Use a capture group that allows nested parentheses in the first arg
    source = re.sub(
        r'\bformat\(\s*([^,]+?(?:\([^)]*\))?)\s*,\s*DATE_FORMAT\s*\)',
        r'format_date(\1)',
        source,
    )
    source = re.sub(
        r"\bformat\(\s*([^,]+?(?:\([^)]*\))?)\s*,\s*['\"]yyyy-MM-dd['\"]\s*\)",
        r'format_date(\1)',
        source,
    )

    # format(date, 'yyyy') -> str(parse_date(date).year)
    source = re.sub(
        r"\bformat\(\s*([^,]+?(?:\([^)]*\))?)\s*,\s*['\"]yyyy['\"]\s*\)",
        r'str(parse_date(\1).year)',
        source,
    )

    # eachDayOfInterval / eachYearOfInterval -> each_*_of_interval(start, end[, step])
    source = _convert_interval_call(source, 'eachDayOfInterval', 'each_day_of_interval')
    source = _convert_interval_call(source, 'eachYearOfInterval', 'each_year_of_interval')

    # startOfWeek(d, { weekStartsOn: n }) -> start_of_week(d, week_starts_on=n)
    # (must come before the simple rename of startOfWeek)
    source = re.sub(
        r'\bstartOfWeek\(\s*([^,)]+)\s*,\s*\{\s*weekStartsOn\s*:\s*(\d+)\s*\}\s*\)',
        r'start_of_week(\1, week_starts_on=\2)',
        source,
    )

    # Convert date interval result property access:
    # dateInterval.endDate stays (Python dict uses same keys)
    # But we need to handle the object property -> dict key access
    # dateInterval.endDate -> dateInterval["end_date"]  or keep as attribute
    # Actually, get_interval_from_date_range returns a dict with snake_case keys
    # endDate -> end_date, startDate -> start_date in the result
    # But the TS code accesses as .endDate, .startDate
    # After syntax transforms, self. prefix and dot access should work if we
    # return a dict-like object. Let's convert the property names:
    source = re.sub(r'\.endDate\b', '["end_date"]', source)
    source = re.sub(r'\.startDate\b', '["start_date"]', source)

    return source


def _convert_class_transformer(source: str) -> str:
    """Convert class-transformer calls.

    plainToClass(Type, obj) -> obj (no-op in Python)
    """
    source = re.sub(
        r'\bplainToClass\(\s*\w+\s*,\s*([^)]+)\)',
        r'\1',
        source,
    )
    return source


def _convert_date_min_max(source: str) -> str:
    """Convert date-fns min/max to Python builtins.

    min([a, b]) -> min(a, b)
    max([a, b]) -> max(a, b)

    Note: only convert the date-fns style where an array is passed.
    """
    # min([a, b]) -> min(a, b) -- unwrap the array
    source = re.sub(
        r'\bmin\(\s*\[([^\]]+)\]\s*\)',
        r'min(\1)',
        source,
    )
    # max([a, b]) -> max(a, b) -- unwrap the array
    source = re.sub(
        r'\bmax\(\s*\[([^\]]+)\]\s*\)',
        r'max(\1)',
        source,
    )
    return source


def _convert_camelcase_methods(source: str) -> str:
    """Convert remaining camelCase method/property names from TS conventions.

    Specific to the Ghostfolio source patterns:
    - .findIndex(fn) -> next((i for i, x in enumerate(arr) if fn(x)), -1)
      Actually, keep .findIndex for now -- it's complex.
    - .toNumber() -> keep (Big has it)
    - .toFixed(n) -> keep (Big has it)
    """
    # findIndex is used like: orders.findIndex(({ itemType }) => { return itemType === 'start'; })
    # After arrow conversion: orders.findIndex(lambda _item: _item.itemType == 'start')
    # Convert to: next((i for i, _item in enumerate(orders) if _item.itemType == 'start'), -1)
    def replace_findindex(m: re.Match) -> str:
        arr = m.group(1)
        lambda_body = m.group(2)
        # Extract the lambda parameter and body
        lambda_match = re.match(r'lambda\s+(\w+):\s*(.+)', lambda_body)
        if lambda_match:
            param = lambda_match.group(1)
            condition = lambda_match.group(2)
            return f'next((i for i, {param} in enumerate({arr}) if {condition}), -1)'
        return f'{arr}.index({lambda_body})'  # fallback

    source = re.sub(
        r'(\w+(?:\.\w+)*)\.findIndex\(\s*(lambda\s+\w+:\s*[^)]+)\s*\)',
        replace_findindex,
        source,
    )

    return source


def apply(source: str) -> str:
    """Apply library transforms to source."""

    # 1. Remove logging lines first (removes entire lines)
    source = _convert_enable_logging(source)
    source = _remove_logging_lines(source)

    # 2. date-fns functions (complex patterns first)
    source = _convert_date_fns(source)

    # 3. date min/max (array-style)
    source = _convert_date_min_max(source)

    # 4. Simple camelCase -> snake_case renames (date-fns + lodash + helpers)
    source = _apply_simple_renames(source)

    # 5. class-transformer
    source = _convert_class_transformer(source)

    # 6. Method conversions (findIndex etc.)
    source = _convert_camelcase_methods(source)

    return source
