"""Date utility functions — equivalents of date-fns for Python."""
from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FORMAT = "yyyy-MM-dd"


def parse_date(s: str) -> date:
    """Parse ISO date string to date object."""
    if isinstance(s, (date, datetime)):
        return s if isinstance(s, date) and not isinstance(s, datetime) else s.date() if isinstance(s, datetime) else s
    return date.fromisoformat(str(s)[:10])


def format_date(d, fmt: str = DATE_FORMAT) -> str:
    """Format date to string."""
    if isinstance(d, str):
        return d[:10]
    if isinstance(d, datetime):
        d = d.date()
    return d.isoformat()


def difference_in_days(a, b) -> int:
    """Return number of days between a and b (a - b)."""
    return (parse_date(a) - parse_date(b)).days


def is_before(a, b) -> bool:
    return parse_date(a) < parse_date(b)


def is_after(a, b) -> bool:
    return parse_date(a) > parse_date(b)


def add_milliseconds(d, ms: int):
    """Add milliseconds to date (returns datetime for sorting)."""
    dt = datetime.combine(parse_date(d), datetime.min.time())
    return dt + timedelta(milliseconds=ms)


def each_day_of_interval(start, end, step: int = 1) -> list[date]:
    """Generate dates from start to end (inclusive) with step."""
    s, e = parse_date(start), parse_date(end)
    result = []
    current = s
    while current <= e:
        result.append(current)
        current += timedelta(days=step)
    return result


def each_year_of_interval(start, end) -> list[date]:
    """Generate Jan 1 of each year from start to end."""
    s, e = parse_date(start), parse_date(end)
    result = []
    year = s.year
    while year <= e.year:
        result.append(date(year, 1, 1))
        year += 1
    return result


def start_of_year(d) -> date:
    return date(parse_date(d).year, 1, 1)


def end_of_year(d) -> date:
    return date(parse_date(d).year, 12, 31)


def start_of_day(d) -> date:
    return parse_date(d)


def end_of_day(d) -> date:
    return parse_date(d)


def start_of_month(d) -> date:
    dd = parse_date(d)
    return date(dd.year, dd.month, 1)


def start_of_week(d, week_starts_on: int = 1) -> date:
    dd = parse_date(d)
    days_ahead = (dd.weekday() - week_starts_on) % 7
    return dd - timedelta(days=days_ahead)


def sub_days(d, n: int) -> date:
    return parse_date(d) - timedelta(days=n)


def sub_years(d, n: int) -> date:
    dd = parse_date(d)
    try:
        return dd.replace(year=dd.year - n)
    except ValueError:
        return dd.replace(year=dd.year - n, day=28)


def is_this_year(d) -> bool:
    return parse_date(d).year == date.today().year


def is_within_interval(d, interval: dict) -> bool:
    dd = parse_date(d)
    return parse_date(interval["start"]) <= dd <= parse_date(interval["end"])


def reset_hours(d) -> date:
    return parse_date(d)


def get_interval_from_date_range(
    range_str: str, portfolio_start=None
) -> dict:
    """Convert date range string to {start_date, end_date}."""
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
        # Year string like '2024'
        year = int(range_str)
        end_date = end_of_year(date(year, 1, 1))
        start_date = max(start_date, date(year, 1, 1))

    return {"start_date": start_date, "end_date": end_date}
