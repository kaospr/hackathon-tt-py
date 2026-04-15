"""Library-specific transforms: date-fns, lodash, console.log, Logger."""
from __future__ import annotations

import re


def _remove_logging_lines(source: str) -> str:
    """Remove console.log, Logger.warn, Logger.debug lines entirely."""
    # Remove entire lines containing console.log(
    source = re.sub(r'^[^\n]*console\.log\([^)]*\)[^\n]*\n?', '', source, flags=re.MULTILINE)
    # console.log with multi-line arguments (opening paren, content spanning lines, closing)
    source = re.sub(
        r'^\s*console\.log\(.*?\);\s*\n?',
        '',
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    # Remove remaining console.log blocks (multi-line template literals etc.)
    # Match: if (ENABLE_LOGGING) { console.log(...) } blocks
    source = re.sub(
        r'if\s*\(\s*PortfolioCalculator\.ENABLE_LOGGING\s*\)\s*\{[^}]*console\.log[^}]*\}',
        '',
        source,
        flags=re.DOTALL,
    )

    # Remove lines with Logger.warn(
    source = re.sub(r'^[^\n]*Logger\.warn\([^)]*\)[^\n]*\n?', '', source, flags=re.MULTILINE)
    # Multi-line Logger.warn
    source = re.sub(
        r'^\s*Logger\.warn\(.*?\);\s*\n?',
        '',
        source,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Remove lines with Logger.debug(
    source = re.sub(r'^[^\n]*Logger\.debug\([^)]*\)[^\n]*\n?', '', source, flags=re.MULTILINE)

    return source


def _convert_enable_logging(source: str) -> str:
    """Convert PortfolioCalculator.ENABLE_LOGGING to False."""
    source = re.sub(
        r'PortfolioCalculator\.ENABLE_LOGGING',
        'False',
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

    # differenceInDays(a, b) -> difference_in_days(a, b)
    source = re.sub(
        r'\bdifferenceInDays\(',
        'difference_in_days(',
        source,
    )

    # isBefore(a, b) -> is_before(a, b)
    source = re.sub(r'\bisBefore\(', 'is_before(', source)

    # isAfter(a, b) -> is_after(a, b)
    source = re.sub(r'\bisAfter\(', 'is_after(', source)

    # addMilliseconds(d, n) -> add_milliseconds(d, n)
    source = re.sub(r'\baddMilliseconds\(', 'add_milliseconds(', source)

    # eachDayOfInterval({ end, start }, { step }) -> each_day_of_interval(start, end, step)
    # Handle: eachDayOfInterval({ end: e, start: s }, { step: n })
    source = re.sub(
        r'\beachDayOfInterval\(\s*\{\s*end\s*(?::\s*(\w+))?\s*,\s*start\s*(?::\s*(\w+))?\s*\}\s*,\s*\{\s*step\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_day_of_interval({start}, {end}, {step})'.format(
            start=m.group(2) or 'start',
            end=m.group(1) or 'end',
            step=m.group(3) or 'step',
        ),
        source,
    )
    # eachDayOfInterval({ end, start }) -> each_day_of_interval(start, end)
    source = re.sub(
        r'\beachDayOfInterval\(\s*\{\s*end\s*(?::\s*(\w+))?\s*,\s*start\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_day_of_interval({start}, {end})'.format(
            start=m.group(2) or 'start',
            end=m.group(1) or 'end',
        ),
        source,
    )
    # Also handle { start, end } order (start first)
    source = re.sub(
        r'\beachDayOfInterval\(\s*\{\s*start\s*(?::\s*(\w+))?\s*,\s*end\s*(?::\s*(\w+))?\s*\}\s*,\s*\{\s*step\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_day_of_interval({start}, {end}, {step})'.format(
            start=m.group(1) or 'start',
            end=m.group(2) or 'end',
            step=m.group(3) or 'step',
        ),
        source,
    )
    source = re.sub(
        r'\beachDayOfInterval\(\s*\{\s*start\s*(?::\s*(\w+))?\s*,\s*end\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_day_of_interval({start}, {end})'.format(
            start=m.group(1) or 'start',
            end=m.group(2) or 'end',
        ),
        source,
    )

    # eachYearOfInterval({ end, start }) -> each_year_of_interval(start, end)
    source = re.sub(
        r'\beachYearOfInterval\(\s*\{\s*end\s*(?::\s*(\w+))?\s*,\s*start\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_year_of_interval({start}, {end})'.format(
            start=m.group(2) or 'start',
            end=m.group(1) or 'end',
        ),
        source,
    )
    source = re.sub(
        r'\beachYearOfInterval\(\s*\{\s*start\s*(?::\s*(\w+))?\s*,\s*end\s*(?::\s*(\w+))?\s*\}\s*\)',
        lambda m: 'each_year_of_interval({start}, {end})'.format(
            start=m.group(1) or 'start',
            end=m.group(2) or 'end',
        ),
        source,
    )

    # startOfYear(d) -> start_of_year(d)
    source = re.sub(r'\bstartOfYear\(', 'start_of_year(', source)

    # endOfYear(d) -> end_of_year(d)
    source = re.sub(r'\bendOfYear\(', 'end_of_year(', source)

    # startOfDay(d) -> start_of_day(d)
    source = re.sub(r'\bstartOfDay\(', 'start_of_day(', source)

    # endOfDay(d) -> end_of_day(d)
    source = re.sub(r'\bendOfDay\(', 'end_of_day(', source)

    # startOfMonth(d) -> start_of_month(d)
    source = re.sub(r'\bstartOfMonth\(', 'start_of_month(', source)

    # startOfWeek(d, { weekStartsOn: n }) -> start_of_week(d, week_starts_on=n)
    source = re.sub(
        r'\bstartOfWeek\(\s*([^,)]+)\s*,\s*\{\s*weekStartsOn\s*:\s*(\d+)\s*\}\s*\)',
        r'start_of_week(\1, week_starts_on=\2)',
        source,
    )
    # startOfWeek(d) -> start_of_week(d)
    source = re.sub(r'\bstartOfWeek\(', 'start_of_week(', source)

    # subDays(d, n) -> sub_days(d, n)
    source = re.sub(r'\bsubDays\(', 'sub_days(', source)

    # subYears(d, n) -> sub_years(d, n)
    source = re.sub(r'\bsubYears\(', 'sub_years(', source)

    # isThisYear(d) -> is_this_year(d)
    source = re.sub(r'\bisThisYear\(', 'is_this_year(', source)

    # isWithinInterval(d, interval) -> is_within_interval(d, interval)
    source = re.sub(r'\bisWithinInterval\(', 'is_within_interval(', source)

    # parseDate(s) -> parse_date(s)
    source = re.sub(r'\bparseDate\(', 'parse_date(', source)

    # resetHours(d) -> reset_hours(d)
    source = re.sub(r'\bresetHours\(', 'reset_hours(', source)

    # getIntervalFromDateRange(range) -> get_interval_from_date_range(range)
    source = re.sub(
        r'\bgetIntervalFromDateRange\(',
        'get_interval_from_date_range(',
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


def _convert_lodash(source: str) -> str:
    """Convert lodash function calls to Python helper equivalents."""

    # cloneDeep(x) -> clone_deep(x)
    source = re.sub(r'\bcloneDeep\(', 'clone_deep(', source)

    # sortBy(arr, fn) -> sort_by(arr, fn)
    source = re.sub(r'\bsortBy\(', 'sort_by(', source)

    # uniqBy(arr, key) -> uniq_by(arr, key)
    source = re.sub(r'\buniqBy\(', 'uniq_by(', source)

    # isNumber(x) -> is_number(x)
    source = re.sub(r'\bisNumber\(', 'is_number(', source)

    # getSum(items) -> get_sum(items)
    source = re.sub(r'\bgetSum\(', 'get_sum(', source)

    # getFactor(type) -> get_factor(type)
    source = re.sub(r'\bgetFactor\(', 'get_factor(', source)

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

    # 2. date-fns functions
    source = _convert_date_fns(source)

    # 3. date min/max (array-style)
    source = _convert_date_min_max(source)

    # 4. lodash functions
    source = _convert_lodash(source)

    # 5. class-transformer
    source = _convert_class_transformer(source)

    # 6. Method conversions (findIndex etc.)
    source = _convert_camelcase_methods(source)

    return source
