"""Date utility functions — equivalents of date-fns for Python."""
from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FORMAT = "yyyy-MM-dd"


def parse_date(s) -> date:
    """Parse ISO date string to date object.

    Accepts: str ("2024-01-15"), date, or datetime objects.
    Always returns a plain date (not datetime).
    """
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    return date.fromisoformat(str(s)[:10])


def format_date(d, fmt: str = DATE_FORMAT) -> str:
    """Format date to ISO string (yyyy-MM-dd)."""
    if isinstance(d, str):
        return d[:10]
    if isinstance(d, datetime):
        d = d.date()
    return d.isoformat()


def difference_in_days(a, b) -> int:
    """Return integer number of days between a and b (a - b)."""
    return (parse_date(a) - parse_date(b)).days


def is_before(a, b) -> bool:
    """Return True if a < b (as dates)."""
    return parse_date(a) < parse_date(b)


def is_after(a, b) -> bool:
    """Return True if a > b (as dates)."""
    return parse_date(a) > parse_date(b)


def add_milliseconds(d, ms: int) -> datetime:
    """Add milliseconds to date (returns datetime for sort ordering).

    Used for sort ordering: start orders sort before same-day orders (ms=1),
    end orders sort after (ms=-1).
    """
    if isinstance(d, datetime):
        dt = d
    else:
        dt = datetime.combine(parse_date(d), datetime.min.time())
    return dt + timedelta(milliseconds=ms)


def each_day_of_interval(start, end=None, *, step: int = 1) -> list[date]:
    """Generate dates from start to end (inclusive) with step.

    Accepts either:
      - each_day_of_interval(start_date, end_date, step=N)
      - each_day_of_interval({"start": ..., "end": ...}, step=N)
    """
    if isinstance(start, dict):
        s = parse_date(start["start"])
        e = parse_date(start["end"])
        # When called with dict first arg, end may carry the step via options dict
        if isinstance(end, dict):
            step = end.get("step", step)
        elif isinstance(end, int):
            step = end
    else:
        s = parse_date(start)
        e = parse_date(end)
    result = []
    current = s
    while current <= e:
        result.append(current)
        current += timedelta(days=step)
    return result


def each_year_of_interval(start, end=None) -> list[date]:
    """Generate Jan 1 of each year from start's year to end's year (inclusive).

    Accepts either:
      - each_year_of_interval(start_date, end_date)
      - each_year_of_interval({"start": ..., "end": ...})
    """
    if isinstance(start, dict):
        s = parse_date(start["start"])
        e = parse_date(start["end"])
    else:
        s = parse_date(start)
        e = parse_date(end)
    result = []
    year = s.year
    while year <= e.year:
        result.append(date(year, 1, 1))
        year += 1
    return result


def start_of_year(d) -> date:
    """Return Jan 1 of the given date's year."""
    return date(parse_date(d).year, 1, 1)


def end_of_year(d) -> date:
    """Return Dec 31 of the given date's year."""
    return date(parse_date(d).year, 12, 31)


def start_of_day(d) -> date:
    """Strip time component, return date at midnight (as date object)."""
    return parse_date(d)


def end_of_day(d) -> date:
    """Return end of day (as date object — time component not needed for date-only ops)."""
    return parse_date(d)


def start_of_month(d) -> date:
    """Return first day of the month for the given date."""
    dd = parse_date(d)
    return date(dd.year, dd.month, 1)


def start_of_week(d, week_starts_on: int = 1) -> date:
    """Return the start of the week for the given date.

    week_starts_on uses date-fns numbering: 0=Sunday, 1=Monday, ..., 6=Saturday.
    Python weekday() uses: 0=Monday, 1=Tuesday, ..., 6=Sunday.
    """
    dd = parse_date(d)
    # Convert date-fns weekStartsOn to Python weekday numbering
    python_weekstart = (week_starts_on - 1) % 7
    days_back = (dd.weekday() - python_weekstart) % 7
    return dd - timedelta(days=days_back)


def sub_days(d, n: int) -> date:
    """Subtract n days from date."""
    return parse_date(d) - timedelta(days=n)


def sub_years(d, n: int) -> date:
    """Subtract n years from date.

    Handles Feb 29 -> Feb 28 when target year is not a leap year.
    """
    dd = parse_date(d)
    try:
        return dd.replace(year=dd.year - n)
    except ValueError:
        # Feb 29 in a leap year -> Feb 28 in non-leap year
        return dd.replace(year=dd.year - n, day=28)


def is_this_year(d) -> bool:
    """Return True if the date is in the current calendar year."""
    return parse_date(d).year == date.today().year


def is_within_interval(d, interval: dict) -> bool:
    """Return True if date is within [start, end] interval (inclusive).

    interval must have 'start' and 'end' keys.
    """
    dd = parse_date(d)
    return parse_date(interval["start"]) <= dd <= parse_date(interval["end"])


def reset_hours(d) -> date:
    """Strip time component from a date/datetime (equivalent to startOfDay)."""
    return parse_date(d)


def min_date(dates) -> date:
    """Return the earliest date from a list. Equivalent to date-fns min()."""
    return min(parse_date(d) for d in dates)


def max_date(dates) -> date:
    """Return the latest date from a list. Equivalent to date-fns max()."""
    return max(parse_date(d) for d in dates)


def is_number(x) -> bool:
    """Check if x is numeric (equivalent to lodash isNumber)."""
    if isinstance(x, bool):
        return False
    return isinstance(x, (int, float))


def get_interval_from_date_range(
    range_str: str, portfolio_start=None
) -> dict:
    """Convert date range string to {startDate, endDate} interval.

    Returns a dict with both camelCase keys (endDate, startDate) matching the
    TypeScript interface, and snake_case keys (end_date, start_date) for
    Pythonic access.

    range_str: '1d', 'mtd', 'wtd', 'ytd', '1y', '5y', 'max', or a year
               string like '2024'.
    portfolio_start: earliest date in the portfolio (date, str, or None).
    """
    today = date.today()
    end_date = today
    start_date = parse_date(portfolio_start) if portfolio_start else date(1970, 1, 1)

    if range_str == "1d":
        candidate = sub_days(today, 1)
        start_date = max(start_date, candidate)
    elif range_str == "mtd":
        candidate = sub_days(start_of_month(today), 1)
        start_date = max(start_date, candidate)
    elif range_str == "wtd":
        candidate = sub_days(start_of_week(today, week_starts_on=1), 1)
        start_date = max(start_date, candidate)
    elif range_str == "ytd":
        candidate = sub_days(start_of_year(today), 1)
        start_date = max(start_date, candidate)
    elif range_str == "1y":
        candidate = sub_years(today, 1)
        start_date = max(start_date, candidate)
    elif range_str == "5y":
        candidate = sub_years(today, 5)
        start_date = max(start_date, candidate)
    elif range_str == "max":
        pass
    else:
        # Year string like '2024', '2023', etc.
        year = int(range_str)
        end_date = end_of_year(date(year, 1, 1))
        start_date = max(start_date, date(year, 1, 1))

    return {
        "endDate": end_date,
        "startDate": start_date,
        "end_date": end_date,
        "start_date": start_date,
    }
