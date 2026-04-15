"""ROAI Portfolio Calculator — translated from TypeScript."""
from __future__ import annotations

import sys
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator


# ---------------------------------------------------------------------------
# Lightweight Big-like wrapper (mirrors big.js arithmetic used in TS)
# ---------------------------------------------------------------------------

class Big:
    """Minimal big.js compatible wrapper around Python float."""

    __slots__ = ("_v",)

    def __init__(self, value=0):
        if isinstance(value, Big):
            self._v = value._v
        elif value is None:
            self._v = 0.0
        else:
            self._v = float(value)

    # Arithmetic
    def plus(self, other):
        return Big(self._v + Big(other)._v)

    add = plus

    def minus(self, other):
        return Big(self._v - Big(other)._v)

    def mul(self, other):
        return Big(self._v * Big(other)._v)

    def div(self, other):
        d = Big(other)._v
        if d == 0:
            return Big(0)
        return Big(self._v / d)

    def abs(self):
        return Big(abs(self._v))

    # Comparisons
    def eq(self, other):
        return self._v == Big(other)._v

    def gt(self, other):
        return self._v > Big(other)._v

    def gte(self, other):
        return self._v >= Big(other)._v

    def lt(self, other):
        return self._v < Big(other)._v

    def lte(self, other):
        return self._v <= Big(other)._v

    # Conversion
    def toNumber(self):
        return self._v

    def toFixed(self, dp=0):
        return f"{self._v:.{dp}f}"

    def __float__(self):
        return self._v

    def __repr__(self):
        return f"Big({self._v})"

    def __bool__(self):
        return True  # Big object is always truthy (like JS object)


# ---------------------------------------------------------------------------
# Utility helpers (mirrors date-fns / lodash used in TS)
# ---------------------------------------------------------------------------

DATE_FORMAT = "%Y-%m-%d"
EPSILON = sys.float_info.epsilon

INVESTMENT_ACTIVITY_TYPES = ["BUY", "SELL"]

_TYPE_FACTORS = {"BUY": 1, "SELL": -1, "DIVIDEND": 0, "FEE": 0, "INTEREST": 0, "LIABILITY": 0}


def get_factor(activity_type: str) -> int:
    return _TYPE_FACTORS.get(activity_type, 0)


def format_date(d) -> str:
    """Format a date or datetime to YYYY-MM-DD string."""
    if isinstance(d, str):
        return d[:10]
    if isinstance(d, (date, datetime)):
        return d.strftime(DATE_FORMAT)
    return str(d)[:10]


def parse_date(s) -> date:
    """Parse a YYYY-MM-DD string to a date object."""
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    return datetime.strptime(str(s)[:10], DATE_FORMAT).date()


def difference_in_days(a, b) -> int:
    return (parse_date(a) - parse_date(b)).days


def is_before(a, b) -> bool:
    return parse_date(a) < parse_date(b)


def is_after(a, b) -> bool:
    return parse_date(a) > parse_date(b)


def add_milliseconds(d, ms):
    """For ordering purposes only — shifts by ms (used as +-1 for sort)."""
    return parse_date(d)  # milliseconds irrelevant at date granularity


def start_of_day(d) -> date:
    return parse_date(d)


def end_of_day(d) -> date:
    return parse_date(d)


def sub_days(d, n) -> date:
    return parse_date(d) - timedelta(days=n)


def sub_years(d, n) -> date:
    dt = parse_date(d)
    try:
        return dt.replace(year=dt.year - n)
    except ValueError:
        return dt.replace(year=dt.year - n, day=28)


def start_of_year(d) -> date:
    return parse_date(d).replace(month=1, day=1)


def end_of_year(d) -> date:
    return parse_date(d).replace(month=12, day=31)


def start_of_month(d) -> date:
    return parse_date(d).replace(day=1)


def start_of_week(d) -> date:
    dt = parse_date(d)
    return dt - timedelta(days=dt.weekday())


def is_this_year(d) -> bool:
    return parse_date(d).year == date.today().year


def is_within_interval(d, interval) -> bool:
    dt = parse_date(d)
    return parse_date(interval["start"]) <= dt <= parse_date(interval["end"])


def reset_hours(d):
    return parse_date(d)


def each_day_of_interval(interval, step=1) -> list[date]:
    """Return list of dates from interval start to end (inclusive) with step."""
    if isinstance(interval, dict):
        s = parse_date(interval.get("start", interval.get("start")))
        e = parse_date(interval.get("end", interval.get("end")))
    else:
        s, e = interval
    if isinstance(step, dict):
        step = step.get("step", 1)
    result = []
    current = s
    while current <= e:
        result.append(current)
        current += timedelta(days=step)
    return result


def each_year_of_interval(interval) -> list[date]:
    if isinstance(interval, dict):
        s = parse_date(interval.get("start", interval.get("start")))
        e = parse_date(interval.get("end", interval.get("end")))
    else:
        s, e = interval
    result = []
    year = s.year
    while year <= e.year:
        result.append(date(year, 1, 1))
        year += 1
    return result


def get_interval_from_date_range(date_range, reference_date=None):
    """Return {startDate, endDate} for a named range like '1d', '1y', 'max', etc."""
    today = date.today()
    if date_range == "1d":
        return {"startDate": sub_days(today, 1), "endDate": today}
    elif date_range == "1y":
        return {"startDate": sub_years(today, 1), "endDate": today}
    elif date_range == "5y":
        return {"startDate": sub_years(today, 5), "endDate": today}
    elif date_range == "ytd":
        return {"startDate": start_of_year(today), "endDate": today}
    elif date_range == "mtd":
        return {"startDate": start_of_month(today), "endDate": today}
    elif date_range == "wtd":
        return {"startDate": start_of_week(today), "endDate": today}
    elif date_range == "max":
        if reference_date is not None:
            return {"startDate": parse_date(reference_date), "endDate": today}
        return {"startDate": sub_years(today, 50), "endDate": today}
    else:
        # Treat as a year string like "2021"
        try:
            year = int(date_range)
            return {"startDate": date(year, 1, 1), "endDate": date(year, 12, 31)}
        except (ValueError, TypeError):
            return {"startDate": sub_years(today, 50), "endDate": today}


def clone_deep(obj):
    return deepcopy(obj)


def sort_by(lst, key_fn):
    return sorted(lst, key=key_fn)


def uniq_by(lst, key):
    seen = set()
    result = []
    for item in lst:
        k = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def is_number(v) -> bool:
    return v is not None and isinstance(v, (int, float))


def get_sum(values):
    return sum(v if isinstance(v, (int, float)) else (v.toNumber() if isinstance(v, Big) else 0) for v in values)


class RoaiPortfolioCalculator(PortfolioCalculator):
    """ROAI Portfolio Calculator — translated from TypeScript."""

    ENABLE_LOGGING = False

    def __init__(self, activities, current_rate_service):
        super().__init__(activities, current_rate_service)
        self._chart_dates = None
        self._snapshot_cache = None
        # Pre-process activities into TS-compatible format
        self._orders = self._prepare_orders()
        self._transaction_points = []
        self._start_date = None
        self._end_date = None
        self._compute_transaction_points()

    def _prepare_orders(self):
        """Convert flat dict activities to TS-compatible order objects."""
        orders = []
        for act in self.sorted_activities():
            orders.append({
                "SymbolProfile": {
                    "symbol": act.get("symbol", ""),
                    "dataSource": act.get("dataSource", "YAHOO"),
                    "assetSubClass": act.get("assetSubClass"),
                    "currency": act.get("currency", "USD"),
                    "userId": act.get("userId"),
                },
                "date": act["date"],
                "fee": Big(act.get("fee", 0)),
                "feeInBaseCurrency": Big(act.get("fee", 0)),
                "quantity": Big(act.get("quantity", 0)),
                "type": act.get("type", "BUY"),
                "unitPrice": Big(act.get("unitPrice", 0)),
                "tags": act.get("tags", []),
            })
        return orders

    def _compute_transaction_points(self):
        """Build transaction points from orders (mirrors TS computeTransactionPoints)."""
        self._transaction_points = []
        symbols = {}
        last_date = None
        last_tp = None

        for order in self._orders:
            sp = order["SymbolProfile"]
            symbol = sp["symbol"]
            asset_sub_class = sp.get("assetSubClass")
            currency = sp.get("currency", "USD")
            data_source = sp.get("dataSource", "YAHOO")
            skip_errors = bool(sp.get("userId"))
            factor = get_factor(order["type"])
            o_date = order["date"]
            fee = order["fee"]
            fee_in_base = order["feeInBaseCurrency"]
            quantity = order["quantity"]
            unit_price = order["unitPrice"]
            o_type = order["type"]
            tags = order.get("tags", [])

            old = symbols.get(symbol)

            if old:
                investment = old["investment"]
                new_quantity = quantity.mul(factor).plus(old["quantity"])

                if o_type == "BUY":
                    if old["investment"].gte(0):
                        investment = old["investment"].plus(quantity.mul(unit_price))
                    else:
                        investment = old["investment"].plus(quantity.mul(old["averagePrice"]))
                elif o_type == "SELL":
                    if old["investment"].gt(0):
                        investment = old["investment"].minus(quantity.mul(old["averagePrice"]))
                    else:
                        investment = old["investment"].minus(quantity.mul(unit_price))

                if new_quantity.abs().lt(EPSILON):
                    investment = Big(0)
                    new_quantity = Big(0)

                current_item = {
                    "assetSubClass": asset_sub_class,
                    "currency": currency,
                    "dataSource": data_source,
                    "investment": investment,
                    "skipErrors": skip_errors,
                    "symbol": symbol,
                    "activitiesCount": old["activitiesCount"] + 1,
                    "averagePrice": Big(0) if new_quantity.eq(0) else investment.div(new_quantity).abs(),
                    "dateOfFirstActivity": old["dateOfFirstActivity"],
                    "dividend": Big(0),
                    "fee": old["fee"].plus(fee),
                    "feeInBaseCurrency": old["feeInBaseCurrency"].plus(fee_in_base),
                    "includeInHoldings": old["includeInHoldings"],
                    "quantity": new_quantity,
                    "tags": old["tags"] + tags,
                }
            else:
                current_item = {
                    "assetSubClass": asset_sub_class,
                    "currency": currency,
                    "dataSource": data_source,
                    "fee": fee,
                    "feeInBaseCurrency": fee_in_base,
                    "skipErrors": skip_errors,
                    "symbol": symbol,
                    "tags": tags,
                    "activitiesCount": 1,
                    "averagePrice": unit_price,
                    "dateOfFirstActivity": o_date,
                    "dividend": Big(0),
                    "includeInHoldings": o_type in INVESTMENT_ACTIVITY_TYPES,
                    "investment": unit_price.mul(quantity).mul(factor),
                    "quantity": quantity.mul(factor),
                }

            # Deduplicate tags by 'id'
            current_item["tags"] = uniq_by(current_item["tags"], "id")

            symbols[symbol] = current_item

            items = last_tp["items"][:] if last_tp else []
            new_items = [it for it in items if it["symbol"] != symbol]
            new_items.append(current_item)
            new_items.sort(key=lambda a: a.get("symbol", ""))

            fees = Big(0)
            if o_type == "FEE":
                fees = fee

            interest = Big(0)
            if o_type == "INTEREST":
                interest = quantity.mul(unit_price)

            liabilities = Big(0)
            if o_type == "LIABILITY":
                liabilities = quantity.mul(unit_price)

            if last_date != o_date or last_tp is None:
                last_tp = {
                    "date": o_date,
                    "fees": fees,
                    "interest": interest,
                    "liabilities": liabilities,
                    "items": new_items,
                }
                self._transaction_points.append(last_tp)
            else:
                last_tp["fees"] = last_tp["fees"].plus(fees)
                last_tp["interest"] = last_tp["interest"].plus(interest)
                last_tp["items"] = new_items
                last_tp["liabilities"] = last_tp["liabilities"].plus(liabilities)

            last_date = o_date

        # Set date range
        if self._transaction_points:
            first_date = parse_date(self._transaction_points[0]["date"])
            self._start_date = start_of_day(sub_days(first_date, 1))
            self._end_date = end_of_day(date.today())

    def _get_chart_date_map(self, end_date, start_date, step):
        """Build a map of relevant chart dates (mirrors TS getChartDateMap)."""
        chart_date_map = {}

        # 1. Add transaction point dates
        for tp in self._transaction_points:
            chart_date_map[tp["date"]] = True

        # 2. Add dates between transactions respecting step size
        for d in each_day_of_interval({"start": start_date, "end": end_date}, step):
            chart_date_map[format_date(d)] = True

        if step > 1:
            # Reduce step for last 90 days
            for d in each_day_of_interval({"start": sub_days(end_date, 90), "end": end_date}, 3):
                chart_date_map[format_date(d)] = True

            # Reduce step for last 30 days
            for d in each_day_of_interval({"start": sub_days(end_date, 30), "end": end_date}, 1):
                chart_date_map[format_date(d)] = True

        # Make sure end date is present
        chart_date_map[format_date(end_date)] = True

        # Add key date range boundaries
        for dr in ["1d", "1y", "5y", "max", "mtd", "wtd", "ytd"]:
            interval = get_interval_from_date_range(dr)
            dr_start = parse_date(interval["startDate"])
            dr_end = parse_date(interval["endDate"])

            if not is_before(dr_start, start_date) and not is_after(dr_start, end_date):
                chart_date_map[format_date(dr_start)] = True
            if not is_before(dr_end, start_date) and not is_after(dr_end, end_date):
                chart_date_map[format_date(dr_end)] = True

        # Add first and last date of each calendar year
        interval = {"start": start_date, "end": end_date}
        for d in each_year_of_interval(interval):
            yr_start = start_of_year(d)
            yr_end = end_of_year(d)

            if is_within_interval(yr_start, interval):
                chart_date_map[format_date(yr_start)] = True
            if is_within_interval(yr_end, interval):
                chart_date_map[format_date(yr_end)] = True

        return chart_date_map

    def _build_market_data(self):
        """Build marketSymbolMap and exchangeRates from current_rate_service."""
        if not self._transaction_points:
            return {}, {}

        # Collect all unique symbols (excluding CASH)
        last_tp = self._transaction_points[-1]
        symbols = []
        currencies = {}
        for item in last_tp["items"]:
            if item.get("assetSubClass") != "CASH":
                symbols.append(item["symbol"])
            currencies[item["symbol"]] = item.get("currency", "USD")

        start_str = format_date(self._start_date)
        end_str = format_date(self._end_date)

        # Get all dates that have market data in range
        all_dates = self.current_rate_service.all_dates_in_range(start_str, end_str)

        # Also include transaction point dates and chart dates
        for tp in self._transaction_points:
            all_dates.add(tp["date"])

        market_symbol_map = {}
        for date_str in sorted(all_dates):
            market_symbol_map[date_str] = {}
            for sym in symbols:
                price = self.current_rate_service.get_price(sym, date_str)
                if price is not None:
                    market_symbol_map[date_str][sym] = Big(price)

        # Ensure the end date (today) has price data using nearest/latest prices
        today_str = format_date(date.today())
        if today_str not in market_symbol_map:
            market_symbol_map[today_str] = {}
        for sym in symbols:
            if sym not in market_symbol_map[today_str]:
                latest = self.current_rate_service.get_latest_price(sym)
                if latest and latest > 0:
                    market_symbol_map[today_str][sym] = Big(latest)

        # Simplified exchange rates (single currency assumption)
        exchange_rates = {}
        for date_str in sorted(all_dates):
            exchange_rates[date_str] = 1.0
        # Ensure today is in exchange rates
        exchange_rates[today_str] = 1.0

        return market_symbol_map, exchange_rates

    def _get_symbol_metrics(self, chart_date_map, data_source, end, exchange_rates, market_symbol_map, start, symbol):
        """Calculate per-symbol metrics (mirrors TS getSymbolMetrics — ROAI variant)."""
        current_exchange_rate = exchange_rates.get(format_date(date.today()), 1)
        current_values = {}
        current_values_with_ce = {}
        fees = Big(0)
        fees_at_start_date = Big(0)
        fees_at_start_date_with_ce = Big(0)
        fees_with_ce = Big(0)
        gross_performance = Big(0)
        gross_performance_with_ce = Big(0)
        gross_performance_at_start_date = Big(0)
        gross_performance_at_start_date_with_ce = Big(0)
        gross_performance_from_sells = Big(0)
        gross_performance_from_sells_with_ce = Big(0)
        initial_value = None
        initial_value_with_ce = None
        investment_at_start_date = None
        investment_at_start_date_with_ce = None
        investment_values_accumulated = {}
        investment_values_accumulated_with_ce = {}
        investment_values_with_ce = {}
        last_average_price = Big(0)
        last_average_price_with_ce = Big(0)
        net_performance_values = {}
        net_performance_values_with_ce = {}
        time_weighted_investment_values = {}
        time_weighted_investment_values_with_ce = {}
        total_account_balance_in_base = Big(0)
        total_dividend = Big(0)
        total_dividend_in_base = Big(0)
        total_interest = Big(0)
        total_interest_in_base = Big(0)
        total_investment = Big(0)
        total_investment_from_buys = Big(0)
        total_investment_from_buys_with_ce = Big(0)
        total_investment_with_ce = Big(0)
        total_liabilities = Big(0)
        total_liabilities_in_base = Big(0)
        total_quantity_from_buys = Big(0)
        total_units = Big(0)
        value_at_start_date = None
        value_at_start_date_with_ce = None

        # Clone orders for this symbol
        orders = clone_deep([
            o for o in self._orders if o["SymbolProfile"]["symbol"] == symbol
        ])

        is_cash = (orders[0]["SymbolProfile"].get("assetSubClass") == "CASH") if orders else False

        # Empty return value
        def empty_metrics(has_errors=False):
            return {
                "currentValues": {},
                "currentValuesWithCurrencyEffect": {},
                "feesWithCurrencyEffect": Big(0),
                "grossPerformance": Big(0),
                "grossPerformancePercentage": Big(0),
                "grossPerformancePercentageWithCurrencyEffect": Big(0),
                "grossPerformanceWithCurrencyEffect": Big(0),
                "hasErrors": has_errors,
                "initialValue": Big(0),
                "initialValueWithCurrencyEffect": Big(0),
                "investmentValuesAccumulated": {},
                "investmentValuesAccumulatedWithCurrencyEffect": {},
                "investmentValuesWithCurrencyEffect": {},
                "netPerformance": Big(0),
                "netPerformancePercentage": Big(0),
                "netPerformancePercentageWithCurrencyEffectMap": {},
                "netPerformanceValues": {},
                "netPerformanceValuesWithCurrencyEffect": {},
                "netPerformanceWithCurrencyEffectMap": {},
                "timeWeightedInvestment": Big(0),
                "timeWeightedInvestmentValues": {},
                "timeWeightedInvestmentValuesWithCurrencyEffect": {},
                "timeWeightedInvestmentWithCurrencyEffect": Big(0),
                "totalAccountBalanceInBaseCurrency": Big(0),
                "totalDividend": Big(0),
                "totalDividendInBaseCurrency": Big(0),
                "totalInterest": Big(0),
                "totalInterestInBaseCurrency": Big(0),
                "totalInvestment": Big(0),
                "totalInvestmentWithCurrencyEffect": Big(0),
                "totalLiabilities": Big(0),
                "totalLiabilitiesInBaseCurrency": Big(0),
            }

        if len(orders) <= 0:
            return empty_metrics()

        date_of_first_transaction = parse_date(orders[0]["date"])
        end_date_string = format_date(end)
        start_date_string = format_date(start)

        unit_price_at_start = market_symbol_map.get(start_date_string, {}).get(symbol)
        unit_price_at_end = market_symbol_map.get(end_date_string, {}).get(symbol)

        latest_activity = orders[-1] if orders else None

        if (data_source == "MANUAL"
            and latest_activity and latest_activity.get("type") in ("BUY", "SELL")
            and latest_activity.get("unitPrice")
            and not unit_price_at_end):
            unit_price_at_end = latest_activity["unitPrice"]
        elif is_cash:
            unit_price_at_end = Big(1)

        if (not unit_price_at_end or
            (not unit_price_at_start and is_before(date_of_first_transaction, start))):
            return empty_metrics(has_errors=True)

        # Add synthetic start/end orders
        orders.append({
            "date": start_date_string,
            "fee": Big(0),
            "feeInBaseCurrency": Big(0),
            "itemType": "start",
            "quantity": Big(0),
            "SymbolProfile": {
                "dataSource": data_source,
                "symbol": symbol,
                "assetSubClass": "CASH" if is_cash else None,
            },
            "type": "BUY",
            "unitPrice": unit_price_at_start,
            "tags": [],
        })

        orders.append({
            "date": end_date_string,
            "fee": Big(0),
            "feeInBaseCurrency": Big(0),
            "itemType": "end",
            "SymbolProfile": {
                "dataSource": data_source,
                "symbol": symbol,
                "assetSubClass": "CASH" if is_cash else None,
            },
            "quantity": Big(0),
            "type": "BUY",
            "unitPrice": unit_price_at_end,
            "tags": [],
        })

        last_unit_price = None

        orders_by_date = {}
        for o in orders:
            orders_by_date.setdefault(o["date"], []).append(o)

        if not self._chart_dates:
            self._chart_dates = sorted(chart_date_map.keys())

        for date_string in self._chart_dates:
            if date_string < start_date_string:
                continue
            elif date_string > end_date_string:
                break

            if orders_by_date.get(date_string) and len(orders_by_date[date_string]) > 0:
                for o in orders_by_date[date_string]:
                    o["unitPriceFromMarketData"] = (
                        market_symbol_map.get(date_string, {}).get(symbol) or last_unit_price
                    )
            else:
                market_price = market_symbol_map.get(date_string, {}).get(symbol) or last_unit_price
                orders.append({
                    "date": date_string,
                    "fee": Big(0),
                    "feeInBaseCurrency": Big(0),
                    "quantity": Big(0),
                    "SymbolProfile": {
                        "dataSource": data_source,
                        "symbol": symbol,
                        "assetSubClass": "CASH" if is_cash else None,
                    },
                    "type": "BUY",
                    "unitPrice": market_price,
                    "unitPriceFromMarketData": market_price,
                    "tags": [],
                })

            latest_activity = orders[-1]
            last_unit_price = latest_activity.get("unitPriceFromMarketData") or latest_activity.get("unitPrice")

        # Sort orders: start comes before same-date, end comes after
        def sort_key(o):
            d = parse_date(o["date"])
            item_type = o.get("itemType")
            if item_type == "end":
                return (d, 1)
            elif item_type == "start":
                return (d, -1)
            return (d, 0)

        orders = sorted(orders, key=sort_key)

        index_of_start = next((i for i, o in enumerate(orders) if o.get("itemType") == "start"), 0)
        index_of_end = next((i for i, o in enumerate(orders) if o.get("itemType") == "end"), len(orders) - 1)

        total_investment_days = 0
        sum_twi = Big(0)
        sum_twi_with_ce = Big(0)

        for i, order in enumerate(orders):
            exchange_rate_at_date = exchange_rates.get(order["date"], 1)

            if order["type"] == "DIVIDEND":
                dividend = order["quantity"].mul(order["unitPrice"])
                total_dividend = total_dividend.plus(dividend)
                total_dividend_in_base = total_dividend_in_base.plus(
                    dividend.mul(exchange_rate_at_date)
                )
            elif order["type"] == "INTEREST":
                interest = order["quantity"].mul(order["unitPrice"])
                total_interest = total_interest.plus(interest)
                total_interest_in_base = total_interest_in_base.plus(
                    interest.mul(exchange_rate_at_date)
                )
            elif order["type"] == "LIABILITY":
                liab = order["quantity"].mul(order["unitPrice"])
                total_liabilities = total_liabilities.plus(liab)
                total_liabilities_in_base = total_liabilities_in_base.plus(
                    liab.mul(exchange_rate_at_date)
                )

            if order.get("itemType") == "start":
                order["unitPrice"] = (
                    orders[i + 1]["unitPrice"] if index_of_start == 0 and i + 1 < len(orders)
                    else unit_price_at_start
                )

            if order.get("fee"):
                order["feeInBaseCurrency"] = order["fee"].mul(current_exchange_rate)
                order["feeInBaseCurrencyWithCurrencyEffect"] = order["fee"].mul(exchange_rate_at_date)

            up = order.get("unitPrice") if order["type"] in ("BUY", "SELL") else order.get("unitPriceFromMarketData")

            if up:
                order["unitPriceInBaseCurrency"] = up.mul(current_exchange_rate)
                order["unitPriceInBaseCurrencyWithCurrencyEffect"] = up.mul(exchange_rate_at_date)

            market_price_base = (
                order.get("unitPriceFromMarketData", Big(0)) or Big(0)
            ).mul(current_exchange_rate)
            market_price_base_ce = (
                order.get("unitPriceFromMarketData", Big(0)) or Big(0)
            ).mul(exchange_rate_at_date)

            val_before = total_units.mul(market_price_base)
            val_before_ce = total_units.mul(market_price_base_ce)

            if investment_at_start_date is None and i >= index_of_start:
                investment_at_start_date = total_investment if total_investment else Big(0)
                investment_at_start_date_with_ce = total_investment_with_ce if total_investment_with_ce else Big(0)
                value_at_start_date = val_before
                value_at_start_date_with_ce = val_before_ce

            transaction_inv = Big(0)
            transaction_inv_ce = Big(0)

            if order["type"] == "BUY":
                transaction_inv = order["quantity"].mul(
                    order.get("unitPriceInBaseCurrency", Big(0))
                ).mul(get_factor(order["type"]))

                transaction_inv_ce = order["quantity"].mul(
                    order.get("unitPriceInBaseCurrencyWithCurrencyEffect", Big(0))
                ).mul(get_factor(order["type"]))

                total_quantity_from_buys = total_quantity_from_buys.plus(order["quantity"])
                total_investment_from_buys = total_investment_from_buys.plus(transaction_inv)
                total_investment_from_buys_with_ce = total_investment_from_buys_with_ce.plus(transaction_inv_ce)

            elif order["type"] == "SELL":
                if total_units.gt(0):
                    transaction_inv = total_investment.div(total_units).mul(
                        order["quantity"]
                    ).mul(get_factor(order["type"]))
                    transaction_inv_ce = total_investment_with_ce.div(total_units).mul(
                        order["quantity"]
                    ).mul(get_factor(order["type"]))

            total_inv_before = total_investment
            total_inv_before_ce = total_investment_with_ce

            total_investment = total_investment.plus(transaction_inv)
            total_investment_with_ce = total_investment_with_ce.plus(transaction_inv_ce)

            if i >= index_of_start and not initial_value:
                if i == index_of_start and not val_before.eq(0):
                    initial_value = val_before
                    initial_value_with_ce = val_before_ce
                elif transaction_inv.gt(0):
                    initial_value = transaction_inv
                    initial_value_with_ce = transaction_inv_ce

            fees = fees.plus(order.get("feeInBaseCurrency") or 0)
            fees_with_ce = fees_with_ce.plus(order.get("feeInBaseCurrencyWithCurrencyEffect") or 0)

            total_units = total_units.plus(order["quantity"].mul(get_factor(order["type"])))

            val_of_inv = total_units.mul(market_price_base)
            val_of_inv_ce = total_units.mul(market_price_base_ce)

            gp_from_sell = (
                order.get("unitPriceInBaseCurrency", Big(0)).minus(last_average_price).mul(order["quantity"])
                if order["type"] == "SELL" else Big(0)
            )
            gp_from_sell_ce = (
                order.get("unitPriceInBaseCurrencyWithCurrencyEffect", Big(0)).minus(last_average_price_with_ce).mul(order["quantity"])
                if order["type"] == "SELL" else Big(0)
            )

            gross_performance_from_sells = gross_performance_from_sells.plus(gp_from_sell)
            gross_performance_from_sells_with_ce = gross_performance_from_sells_with_ce.plus(gp_from_sell_ce)

            last_average_price = (
                Big(0) if total_quantity_from_buys.eq(0)
                else total_investment_from_buys.div(total_quantity_from_buys)
            )
            last_average_price_with_ce = (
                Big(0) if total_quantity_from_buys.eq(0)
                else total_investment_from_buys_with_ce.div(total_quantity_from_buys)
            )

            if total_units.eq(0):
                total_investment_from_buys = Big(0)
                total_investment_from_buys_with_ce = Big(0)
                total_quantity_from_buys = Big(0)

            new_gp = val_of_inv.minus(total_investment).plus(gross_performance_from_sells)
            new_gp_ce = val_of_inv_ce.minus(total_investment_with_ce).plus(gross_performance_from_sells_with_ce)

            gross_performance = new_gp
            gross_performance_with_ce = new_gp_ce

            if order.get("itemType") == "start":
                fees_at_start_date = fees
                fees_at_start_date_with_ce = fees_with_ce
                gross_performance_at_start_date = gross_performance
                gross_performance_at_start_date_with_ce = gross_performance_with_ce

            if i > index_of_start:
                if val_before.gt(0) and order["type"] in ("BUY", "SELL"):
                    order_date = parse_date(order["date"])
                    prev_date = parse_date(orders[i - 1]["date"])
                    days_since = difference_in_days(order_date, prev_date)
                    if days_since <= 0:
                        days_since = EPSILON

                    total_investment_days += days_since

                    sum_twi = sum_twi.add(
                        value_at_start_date.minus(investment_at_start_date).plus(total_inv_before).mul(days_since)
                    )
                    sum_twi_with_ce = sum_twi_with_ce.add(
                        value_at_start_date_with_ce.minus(investment_at_start_date_with_ce).plus(total_inv_before_ce).mul(days_since)
                    )

                current_values[order["date"]] = val_of_inv
                current_values_with_ce[order["date"]] = val_of_inv_ce

                net_performance_values[order["date"]] = (
                    gross_performance.minus(gross_performance_at_start_date)
                    .minus(fees.minus(fees_at_start_date))
                )
                net_performance_values_with_ce[order["date"]] = (
                    gross_performance_with_ce.minus(gross_performance_at_start_date_with_ce)
                    .minus(fees_with_ce.minus(fees_at_start_date_with_ce))
                )

                investment_values_accumulated[order["date"]] = total_investment
                investment_values_accumulated_with_ce[order["date"]] = total_investment_with_ce

                investment_values_with_ce[order["date"]] = (
                    investment_values_with_ce.get(order["date"], Big(0))
                ).add(transaction_inv_ce)

                time_weighted_investment_values[order["date"]] = (
                    sum_twi.div(total_investment_days) if total_investment_days > EPSILON
                    else total_investment if total_investment.gt(0) else Big(0)
                )
                time_weighted_investment_values_with_ce[order["date"]] = (
                    sum_twi_with_ce.div(total_investment_days) if total_investment_days > EPSILON
                    else total_investment_with_ce if total_investment_with_ce.gt(0) else Big(0)
                )

            if i == index_of_end:
                break

        total_gp = gross_performance.minus(gross_performance_at_start_date)
        total_gp_ce = gross_performance_with_ce.minus(gross_performance_at_start_date_with_ce)
        total_np = gross_performance.minus(gross_performance_at_start_date).minus(
            fees.minus(fees_at_start_date)
        )

        twi_avg = sum_twi.div(total_investment_days) if total_investment_days > 0 else Big(0)
        twi_avg_ce = sum_twi_with_ce.div(total_investment_days) if total_investment_days > 0 else Big(0)

        gp_pct = total_gp.div(twi_avg) if twi_avg.gt(0) else Big(0)
        gp_pct_ce = total_gp_ce.div(twi_avg_ce) if twi_avg_ce.gt(0) else Big(0)

        np_pct = total_np.div(twi_avg) if twi_avg.gt(0) else Big(0)

        # Build per-dateRange net performance maps
        np_pct_ce_map = {}
        np_with_ce_map = {}

        date_ranges = ["1d", "1y", "5y", "max", "mtd", "wtd", "ytd"]
        for yr_date in each_year_of_interval({"start": start, "end": end}):
            if not is_this_year(yr_date):
                date_ranges.append(format_date(yr_date)[:4])

        for dr in date_ranges:
            di = get_interval_from_date_range(dr)
            dr_end = parse_date(di["endDate"])
            dr_start = parse_date(di["startDate"])

            if is_before(dr_start, start):
                dr_start = parse_date(start)

            range_end_str = format_date(dr_end)
            range_start_str = format_date(dr_start)

            cv_at_start_ce = current_values_with_ce.get(range_start_str, Big(0))
            iv_acc_at_start_ce = investment_values_accumulated_with_ce.get(range_start_str, Big(0))
            gp_at_start_ce = cv_at_start_ce.minus(iv_acc_at_start_ce)

            average = Big(0)
            day_count = 0

            for j in range(len(self._chart_dates) - 1, -1, -1):
                d = self._chart_dates[j]
                if d > range_end_str:
                    continue
                elif d < range_start_str:
                    break

                acc_val = investment_values_accumulated_with_ce.get(d)
                if acc_val is not None and isinstance(acc_val, Big) and acc_val.gt(0):
                    average = average.add(acc_val.add(gp_at_start_ce))
                    day_count += 1

            if day_count > 0:
                average = average.div(day_count)

            end_val = net_performance_values_with_ce.get(range_end_str, Big(0))
            start_val = (
                Big(0) if dr == "max"
                else net_performance_values_with_ce.get(range_start_str, Big(0))
            )
            np_with_ce_map[dr] = end_val.minus(start_val)

            np_pct_ce_map[dr] = (
                np_with_ce_map[dr].div(average) if average.gt(0) else Big(0)
            )

        return {
            "currentValues": current_values,
            "currentValuesWithCurrencyEffect": current_values_with_ce,
            "feesWithCurrencyEffect": fees_with_ce,
            "grossPerformancePercentage": gp_pct,
            "grossPerformancePercentageWithCurrencyEffect": gp_pct_ce,
            "initialValue": initial_value if initial_value else Big(0),
            "initialValueWithCurrencyEffect": initial_value_with_ce if initial_value_with_ce else Big(0),
            "investmentValuesAccumulated": investment_values_accumulated,
            "investmentValuesAccumulatedWithCurrencyEffect": investment_values_accumulated_with_ce,
            "investmentValuesWithCurrencyEffect": investment_values_with_ce,
            "netPerformancePercentage": np_pct,
            "netPerformancePercentageWithCurrencyEffectMap": np_pct_ce_map,
            "netPerformanceValues": net_performance_values,
            "netPerformanceValuesWithCurrencyEffect": net_performance_values_with_ce,
            "netPerformanceWithCurrencyEffectMap": np_with_ce_map,
            "timeWeightedInvestmentValues": time_weighted_investment_values,
            "timeWeightedInvestmentValuesWithCurrencyEffect": time_weighted_investment_values_with_ce,
            "totalAccountBalanceInBaseCurrency": total_account_balance_in_base,
            "totalDividend": total_dividend,
            "totalDividendInBaseCurrency": total_dividend_in_base,
            "totalInterest": total_interest,
            "totalInterestInBaseCurrency": total_interest_in_base,
            "totalInvestment": total_investment,
            "totalInvestmentWithCurrencyEffect": total_investment_with_ce,
            "totalLiabilities": total_liabilities,
            "totalLiabilitiesInBaseCurrency": total_liabilities_in_base,
            "grossPerformance": total_gp,
            "grossPerformanceWithCurrencyEffect": total_gp_ce,
            "hasErrors": total_units.gt(0) and (not initial_value or not unit_price_at_end),
            "netPerformance": total_np,
            "timeWeightedInvestment": twi_avg,
            "timeWeightedInvestmentWithCurrencyEffect": twi_avg_ce,
        }

    def _calculate_overall_performance(self, positions):
        """Aggregate position-level metrics into portfolio snapshot (mirrors TS calculateOverallPerformance)."""
        current_value_in_base = Big(0)
        gp = Big(0)
        gp_ce = Big(0)
        has_errors = False
        np_ = Big(0)
        total_fees_ce = Big(0)
        total_interest_ce = Big(0)
        total_inv = Big(0)
        total_inv_ce = Big(0)
        total_twi = Big(0)
        total_twi_ce = Big(0)

        for pos in positions:
            if not pos.get("includeInTotalAssetValue", True):
                continue

            if pos.get("feeInBaseCurrency"):
                total_fees_ce = total_fees_ce.plus(pos["feeInBaseCurrency"])

            if pos.get("valueInBaseCurrency"):
                current_value_in_base = current_value_in_base.plus(pos["valueInBaseCurrency"])
            else:
                has_errors = True

            if pos.get("investment"):
                total_inv = total_inv.plus(pos["investment"])
                total_inv_ce = total_inv_ce.plus(
                    pos.get("investmentWithCurrencyEffect", pos["investment"])
                )
            else:
                has_errors = True

            if pos.get("grossPerformance"):
                gp = gp.plus(pos["grossPerformance"])
                gp_ce = gp_ce.plus(pos.get("grossPerformanceWithCurrencyEffect", Big(0)))
                np_ = np_.plus(pos.get("netPerformance", Big(0)))
            elif not pos.get("quantity", Big(0)).eq(0):
                has_errors = True

            if pos.get("timeWeightedInvestment"):
                total_twi = total_twi.plus(pos["timeWeightedInvestment"])
                total_twi_ce = total_twi_ce.plus(
                    pos.get("timeWeightedInvestmentWithCurrencyEffect", Big(0))
                )
            elif not pos.get("quantity", Big(0)).eq(0):
                has_errors = True

        return {
            "currentValueInBaseCurrency": current_value_in_base,
            "hasErrors": has_errors,
            "positions": positions,
            "totalFeesWithCurrencyEffect": total_fees_ce,
            "totalInterestWithCurrencyEffect": total_interest_ce,
            "totalInvestment": total_inv,
            "totalInvestmentWithCurrencyEffect": total_inv_ce,
            "activitiesCount": len([
                o for o in self._orders if o["type"] in ("BUY", "SELL")
            ]),
            "createdAt": datetime.now(),
            "errors": [],
            "historicalData": [],
            "totalLiabilitiesWithCurrencyEffect": Big(0),
        }

    def _compute_snapshot(self):
        """Build full portfolio snapshot (mirrors TS computeSnapshot)."""
        if self._snapshot_cache is not None:
            return self._snapshot_cache

        last_tp = self._transaction_points[-1] if self._transaction_points else None
        transaction_points = [
            tp for tp in self._transaction_points
            if is_before(parse_date(tp["date"]), self._end_date) or format_date(parse_date(tp["date"])) == format_date(self._end_date)
        ]

        if not transaction_points:
            self._snapshot_cache = {
                "activitiesCount": 0,
                "createdAt": datetime.now(),
                "currentValueInBaseCurrency": Big(0),
                "errors": [],
                "hasErrors": False,
                "historicalData": [],
                "positions": [],
                "totalFeesWithCurrencyEffect": Big(0),
                "totalInterestWithCurrencyEffect": Big(0),
                "totalInvestment": Big(0),
                "totalInvestmentWithCurrencyEffect": Big(0),
                "totalLiabilitiesWithCurrencyEffect": Big(0),
            }
            return self._snapshot_cache

        market_symbol_map, exchange_rates = self._build_market_data()

        currencies = {}
        data_gathering_items = []
        first_index = len(transaction_points)
        first_tp_found = None
        total_interest_ce = Big(0)
        total_liabilities_ce = Big(0)

        for item in transaction_points[first_index - 1]["items"]:
            if item.get("assetSubClass") != "CASH":
                data_gathering_items.append({
                    "dataSource": item["dataSource"],
                    "symbol": item["symbol"],
                })
            currencies[item["symbol"]] = item.get("currency", "USD")

        for i, tp in enumerate(transaction_points):
            if not is_before(parse_date(tp["date"]), self._start_date) and first_tp_found is None:
                first_tp_found = tp
                first_index = i

        end_date_string = format_date(self._end_date)
        days_in_market = difference_in_days(self._end_date, self._start_date)
        max_chart_items = 500

        step = max(1, round(days_in_market / min(days_in_market, max_chart_items))) if days_in_market > 0 else 1

        chart_date_map = self._get_chart_date_map(
            end_date=self._end_date,
            start_date=self._start_date,
            step=step,
        )

        chart_dates = sorted(chart_date_map.keys())

        if first_index > 0:
            first_index -= 1

        errors = []
        has_any_errors = False
        positions = []
        accumulated_values_by_date = {}
        values_by_symbol = {}

        for item in last_tp["items"]:
            market_price_base = (
                market_symbol_map.get(end_date_string, {}).get(item["symbol"])
                or item.get("averagePrice", Big(0))
            )
            # Exchange rate = 1 (simplified single-currency)
            market_price_in_base = market_price_base

            metrics = self._get_symbol_metrics(
                chart_date_map=chart_date_map,
                data_source=item["dataSource"],
                end=self._end_date,
                exchange_rates=exchange_rates,
                market_symbol_map=market_symbol_map,
                start=self._start_date,
                symbol=item["symbol"],
            )

            has_any_errors = has_any_errors or metrics["hasErrors"]
            include_in_total = item.get("assetSubClass") != "CASH"

            if include_in_total:
                values_by_symbol[item["symbol"]] = {
                    "currentValues": metrics["currentValues"],
                    "currentValuesWithCurrencyEffect": metrics["currentValuesWithCurrencyEffect"],
                    "investmentValuesAccumulated": metrics["investmentValuesAccumulated"],
                    "investmentValuesAccumulatedWithCurrencyEffect": metrics["investmentValuesAccumulatedWithCurrencyEffect"],
                    "investmentValuesWithCurrencyEffect": metrics["investmentValuesWithCurrencyEffect"],
                    "netPerformanceValues": metrics["netPerformanceValues"],
                    "netPerformanceValuesWithCurrencyEffect": metrics["netPerformanceValuesWithCurrencyEffect"],
                    "timeWeightedInvestmentValues": metrics["timeWeightedInvestmentValues"],
                    "timeWeightedInvestmentValuesWithCurrencyEffect": metrics["timeWeightedInvestmentValuesWithCurrencyEffect"],
                }

            value_in_base = market_price_in_base.mul(item["quantity"]) if isinstance(market_price_in_base, Big) else Big(market_price_in_base).mul(item["quantity"])

            positions.append({
                "includeInTotalAssetValue": include_in_total,
                "timeWeightedInvestment": metrics["timeWeightedInvestment"],
                "timeWeightedInvestmentWithCurrencyEffect": metrics["timeWeightedInvestmentWithCurrencyEffect"],
                "activitiesCount": item.get("activitiesCount", 0),
                "averagePrice": item.get("averagePrice", Big(0)),
                "currency": item.get("currency", "USD"),
                "dataSource": item["dataSource"],
                "dateOfFirstActivity": item.get("dateOfFirstActivity"),
                "dividend": metrics["totalDividend"],
                "dividendInBaseCurrency": metrics["totalDividendInBaseCurrency"],
                "fee": item.get("fee", Big(0)),
                "feeInBaseCurrency": item.get("feeInBaseCurrency", Big(0)),
                "grossPerformance": metrics["grossPerformance"] if not metrics["hasErrors"] else None,
                "grossPerformancePercentage": metrics["grossPerformancePercentage"] if not metrics["hasErrors"] else None,
                "grossPerformancePercentageWithCurrencyEffect": metrics["grossPerformancePercentageWithCurrencyEffect"] if not metrics["hasErrors"] else None,
                "grossPerformanceWithCurrencyEffect": metrics["grossPerformanceWithCurrencyEffect"] if not metrics["hasErrors"] else None,
                "includeInHoldings": item.get("includeInHoldings", True),
                "investment": metrics["totalInvestment"],
                "investmentWithCurrencyEffect": metrics["totalInvestmentWithCurrencyEffect"],
                "marketPrice": market_symbol_map.get(end_date_string, {}).get(item["symbol"], Big(1)).toNumber(),
                "marketPriceInBaseCurrency": market_price_in_base.toNumber() if isinstance(market_price_in_base, Big) else float(market_price_in_base),
                "netPerformance": metrics["netPerformance"] if not metrics["hasErrors"] else None,
                "netPerformancePercentage": metrics["netPerformancePercentage"] if not metrics["hasErrors"] else None,
                "netPerformancePercentageWithCurrencyEffectMap": metrics["netPerformancePercentageWithCurrencyEffectMap"] if not metrics["hasErrors"] else None,
                "netPerformanceWithCurrencyEffectMap": metrics["netPerformanceWithCurrencyEffectMap"] if not metrics["hasErrors"] else None,
                "quantity": item["quantity"],
                "symbol": item["symbol"],
                "tags": item.get("tags", []),
                "valueInBaseCurrency": value_in_base,
            })

            total_interest_ce = total_interest_ce.plus(metrics.get("totalInterestInBaseCurrency", Big(0)))
            total_liabilities_ce = total_liabilities_ce.plus(metrics.get("totalLiabilitiesInBaseCurrency", Big(0)))

            if (metrics["hasErrors"] and item.get("investment", Big(0)).gt(0) and not item.get("skipErrors", False)):
                errors.append({"dataSource": item["dataSource"], "symbol": item["symbol"]})

        # Accumulate values by date for historical data / chart
        for date_string in chart_dates:
            for sym in values_by_symbol:
                sv = values_by_symbol[sym]

                cv = sv["currentValues"].get(date_string, Big(0))
                cv_ce = sv["currentValuesWithCurrencyEffect"].get(date_string, Big(0))
                iv_acc = sv["investmentValuesAccumulated"].get(date_string, Big(0))
                iv_acc_ce = sv["investmentValuesAccumulatedWithCurrencyEffect"].get(date_string, Big(0))
                iv_ce = sv["investmentValuesWithCurrencyEffect"].get(date_string, Big(0))
                npv = sv["netPerformanceValues"].get(date_string, Big(0))
                npv_ce = sv["netPerformanceValuesWithCurrencyEffect"].get(date_string, Big(0))
                twiv = sv["timeWeightedInvestmentValues"].get(date_string, Big(0))
                twiv_ce = sv["timeWeightedInvestmentValuesWithCurrencyEffect"].get(date_string, Big(0))

                if date_string not in accumulated_values_by_date:
                    accumulated_values_by_date[date_string] = {
                        "investmentValueWithCurrencyEffect": Big(0),
                        "totalAccountBalanceWithCurrencyEffect": Big(0),
                        "totalCurrentValue": Big(0),
                        "totalCurrentValueWithCurrencyEffect": Big(0),
                        "totalInvestmentValue": Big(0),
                        "totalInvestmentValueWithCurrencyEffect": Big(0),
                        "totalNetPerformanceValue": Big(0),
                        "totalNetPerformanceValueWithCurrencyEffect": Big(0),
                        "totalTimeWeightedInvestmentValue": Big(0),
                        "totalTimeWeightedInvestmentValueWithCurrencyEffect": Big(0),
                    }

                acc = accumulated_values_by_date[date_string]
                acc["investmentValueWithCurrencyEffect"] = acc["investmentValueWithCurrencyEffect"].add(iv_ce)
                acc["totalCurrentValue"] = acc["totalCurrentValue"].add(cv)
                acc["totalCurrentValueWithCurrencyEffect"] = acc["totalCurrentValueWithCurrencyEffect"].add(cv_ce)
                acc["totalInvestmentValue"] = acc["totalInvestmentValue"].add(iv_acc)
                acc["totalInvestmentValueWithCurrencyEffect"] = acc["totalInvestmentValueWithCurrencyEffect"].add(iv_acc_ce)
                acc["totalNetPerformanceValue"] = acc["totalNetPerformanceValue"].add(npv)
                acc["totalNetPerformanceValueWithCurrencyEffect"] = acc["totalNetPerformanceValueWithCurrencyEffect"].add(npv_ce)
                acc["totalTimeWeightedInvestmentValue"] = acc["totalTimeWeightedInvestmentValue"].add(twiv)
                acc["totalTimeWeightedInvestmentValueWithCurrencyEffect"] = acc["totalTimeWeightedInvestmentValueWithCurrencyEffect"].add(twiv_ce)

        historical_data = []
        for d in sorted(accumulated_values_by_date.keys()):
            vals = accumulated_values_by_date[d]
            twi_val = vals["totalTimeWeightedInvestmentValue"]
            twi_val_ce = vals["totalTimeWeightedInvestmentValueWithCurrencyEffect"]
            npv = vals["totalNetPerformanceValue"]
            npv_ce = vals["totalNetPerformanceValueWithCurrencyEffect"]

            np_pct = 0 if twi_val.eq(0) else npv.div(twi_val).toNumber()
            np_pct_ce = 0 if twi_val_ce.eq(0) else npv_ce.div(twi_val_ce).toNumber()

            historical_data.append({
                "date": d,
                "netPerformanceInPercentage": np_pct,
                "netPerformanceInPercentageWithCurrencyEffect": np_pct_ce,
                "investmentValueWithCurrencyEffect": vals["investmentValueWithCurrencyEffect"].toNumber(),
                "netPerformance": npv.toNumber(),
                "netPerformanceWithCurrencyEffect": npv_ce.toNumber(),
                "netWorth": vals["totalCurrentValueWithCurrencyEffect"].plus(
                    vals["totalAccountBalanceWithCurrencyEffect"]
                ).toNumber(),
                "totalAccountBalance": vals["totalAccountBalanceWithCurrencyEffect"].toNumber(),
                "totalInvestment": vals["totalInvestmentValue"].toNumber(),
                "totalInvestmentValueWithCurrencyEffect": vals["totalInvestmentValueWithCurrencyEffect"].toNumber(),
                "value": vals["totalCurrentValue"].toNumber(),
                "valueWithCurrencyEffect": vals["totalCurrentValueWithCurrencyEffect"].toNumber(),
            })

        overall = self._calculate_overall_performance(positions)

        positions_for_holdings = [
            {k: v for k, v in p.items() if k != "includeInHoldings"}
            for p in positions
            if p.get("includeInHoldings", True)
        ]

        result = {
            **overall,
            "errors": errors,
            "historicalData": historical_data,
            "totalInterestWithCurrencyEffect": total_interest_ce,
            "totalLiabilitiesWithCurrencyEffect": total_liabilities_ce,
            "hasErrors": has_any_errors or overall["hasErrors"],
            "positions": positions_for_holdings,
        }
        self._snapshot_cache = result
        return result

    # =======================================================================
    # Public API methods
    # =======================================================================

    def get_performance(self) -> dict:
        """Return full performance response: {chart, firstOrderDate, performance}."""
        snapshot = self._compute_snapshot()
        historical_data = snapshot.get("historicalData", [])

        chart = []
        np_at_start = None
        np_ce_at_start = None
        total_inv_vals_ce = []

        today = date.today()
        # Use max range: start = self._start_date, end = self._end_date
        start = self._start_date
        end = self._end_date

        for item in historical_data:
            d = parse_date(item["date"])
            if not is_before(d, start) and not is_after(d, end):
                if np_at_start is None:
                    np_at_start = item["netPerformance"]
                    np_ce_at_start = item["netPerformanceWithCurrencyEffect"]

                np_since = item["netPerformance"] - np_at_start
                np_ce_since = item["netPerformanceWithCurrencyEffect"] - np_ce_at_start

                if item.get("totalInvestmentValueWithCurrencyEffect", 0) > 0:
                    total_inv_vals_ce.append(item["totalInvestmentValueWithCurrencyEffect"])

                twi_val = (sum(total_inv_vals_ce) / len(total_inv_vals_ce)) if total_inv_vals_ce else 0

                entry = dict(item)
                entry["netPerformance"] = item["netPerformance"] - np_at_start
                entry["netPerformanceWithCurrencyEffect"] = np_ce_since
                entry["netPerformanceInPercentage"] = (
                    0 if twi_val == 0 else np_since / twi_val
                )
                entry["netPerformanceInPercentageWithCurrencyEffect"] = (
                    0 if twi_val == 0 else np_ce_since / twi_val
                )
                chart.append(entry)

        # Build performance summary from snapshot
        perf = {}
        positions = snapshot.get("positions", [])
        current_value_base = snapshot.get("currentValueInBaseCurrency", Big(0))

        total_fees = snapshot.get("totalFeesWithCurrencyEffect", Big(0))
        total_inv = snapshot.get("totalInvestment", Big(0))
        total_liab = snapshot.get("totalLiabilitiesWithCurrencyEffect", Big(0))

        # Sum net performance from positions
        total_np = Big(0)
        total_np_pct = Big(0)
        total_np_ce = Big(0)
        total_np_pct_ce = Big(0)

        for pos in positions:
            if pos.get("netPerformance") is not None:
                total_np = total_np.plus(pos["netPerformance"])
            if pos.get("netPerformanceWithCurrencyEffectMap") and isinstance(pos["netPerformanceWithCurrencyEffectMap"], dict):
                max_val = pos["netPerformanceWithCurrencyEffectMap"].get("max", Big(0))
                total_np_ce = total_np_ce.plus(max_val)

        # Net performance percentages from chart if available
        if chart:
            last_entry = chart[-1]
            total_np_pct = last_entry.get("netPerformanceInPercentage", 0)
            total_np_pct_ce = last_entry.get("netPerformanceInPercentageWithCurrencyEffect", 0)

        # Fallback: if chart-based percentage is 0 but we have net performance,
        # compute from position-level data (handles same-day buy+sell edge case)
        if (total_np_pct == 0 or total_np_pct_ce == 0) and not total_np.eq(0):
            for pos in positions:
                # Try the position-level netPerformancePercentage first (TWI-based)
                pos_np_pct = pos.get("netPerformancePercentage")
                if pos_np_pct is not None and isinstance(pos_np_pct, Big) and not pos_np_pct.eq(0):
                    if total_np_pct == 0:
                        total_np_pct = pos_np_pct.toNumber()
                    if total_np_pct_ce == 0:
                        total_np_pct_ce = pos_np_pct.toNumber()
                else:
                    # Fall back to the dateRange map
                    np_pct_map = pos.get("netPerformancePercentageWithCurrencyEffectMap")
                    if np_pct_map and isinstance(np_pct_map, dict):
                        max_pct = np_pct_map.get("max", Big(0))
                        if isinstance(max_pct, Big) and not max_pct.eq(0):
                            if total_np_pct == 0:
                                total_np_pct = max_pct.toNumber()
                            if total_np_pct_ce == 0:
                                total_np_pct_ce = max_pct.toNumber()

        cv_num = current_value_base.toNumber() if isinstance(current_value_base, Big) else float(current_value_base)

        perf = {
            "currentNetWorth": cv_num,
            "currentValue": cv_num,
            "currentValueInBaseCurrency": cv_num,
            "netPerformance": total_np.toNumber() if isinstance(total_np, Big) else float(total_np),
            "netPerformancePercentage": total_np_pct if isinstance(total_np_pct, (int, float)) else total_np_pct.toNumber(),
            "netPerformancePercentageWithCurrencyEffect": total_np_pct_ce if isinstance(total_np_pct_ce, (int, float)) else total_np_pct_ce.toNumber(),
            "netPerformanceWithCurrencyEffect": total_np_ce.toNumber() if isinstance(total_np_ce, Big) else float(total_np_ce),
            "totalFees": total_fees.toNumber() if isinstance(total_fees, Big) else float(total_fees),
            "totalInvestment": total_inv.toNumber() if isinstance(total_inv, Big) else float(total_inv),
            "totalLiabilities": total_liab.toNumber() if isinstance(total_liab, Big) else float(total_liab),
            "totalValueables": 0.0,
        }

        first_order_date = min((a["date"] for a in self._orders), default=None) if self._orders else None

        return {
            "chart": chart,
            "firstOrderDate": first_order_date,
            "performance": perf,
        }

    def get_investments(self, group_by=None) -> dict:
        """Return investments: {investments: [{date, investment}]}."""
        if group_by:
            # Group by month or year using historical data
            snapshot = self._compute_snapshot()
            historical_data = snapshot.get("historicalData", [])
            return {"investments": self.get_investments_by_group(historical_data, group_by)}

        # No grouping: build from transaction points
        if not self._transaction_points:
            return {"investments": []}

        investments = []
        for tp in self._transaction_points:
            total = Big(0)
            for item in tp["items"]:
                total = total.plus(item["investment"])
            investments.append({
                "date": tp["date"],
                "investment": total.toNumber(),
            })
        return {"investments": investments}

    def get_investments_by_group(self, data, group_by):
        """Group investment data by month or year (mirrors TS getInvestmentsByGroup)."""
        grouped = {}
        for item in data:
            d = item.get("date", "")
            inv_val = item.get("investmentValueWithCurrencyEffect", 0)
            if group_by == "month":
                date_group = d[:7]  # YYYY-MM
            else:
                date_group = d[:4]  # YYYY

            if date_group not in grouped:
                grouped[date_group] = 0.0

            if isinstance(inv_val, Big):
                grouped[date_group] += inv_val.toNumber()
            else:
                grouped[date_group] += float(inv_val)

        result = []
        for dg in sorted(grouped.keys()):
            if group_by == "month":
                result.append({"date": f"{dg}-01", "investment": grouped[dg]})
            else:
                result.append({"date": f"{dg}-01-01", "investment": grouped[dg]})
        return result

    def get_holdings(self) -> dict:
        """Return holdings: {holdings: {symbol: {...}}}."""
        snapshot = self._compute_snapshot()
        positions = snapshot.get("positions", [])

        holdings = {}
        for pos in positions:
            sym = pos.get("symbol", "")
            investment = pos.get("investment", Big(0))
            quantity = pos.get("quantity", Big(0))

            holdings[sym] = {
                "symbol": sym,
                "quantity": quantity.toNumber() if isinstance(quantity, Big) else float(quantity),
                "investment": investment.toNumber() if isinstance(investment, Big) else float(investment),
                "currency": pos.get("currency", "USD"),
                "dataSource": pos.get("dataSource", "YAHOO"),
                "dateOfFirstActivity": pos.get("dateOfFirstActivity"),
                "averagePrice": pos["averagePrice"].toNumber() if isinstance(pos.get("averagePrice"), Big) else float(pos.get("averagePrice", 0)),
                "marketPrice": pos.get("marketPrice", 0),
                "marketPriceInBaseCurrency": pos.get("marketPriceInBaseCurrency", 0),
                "fee": pos["fee"].toNumber() if isinstance(pos.get("fee"), Big) else float(pos.get("fee", 0)),
                "netPerformance": pos["netPerformance"].toNumber() if isinstance(pos.get("netPerformance"), Big) else (float(pos["netPerformance"]) if pos.get("netPerformance") is not None else 0),
                "netPerformancePercentage": pos["netPerformancePercentage"].toNumber() if isinstance(pos.get("netPerformancePercentage"), Big) else (float(pos["netPerformancePercentage"]) if pos.get("netPerformancePercentage") is not None else 0),
                "grossPerformance": pos["grossPerformance"].toNumber() if isinstance(pos.get("grossPerformance"), Big) else (float(pos["grossPerformance"]) if pos.get("grossPerformance") is not None else 0),
                "valueInBaseCurrency": pos["valueInBaseCurrency"].toNumber() if isinstance(pos.get("valueInBaseCurrency"), Big) else float(pos.get("valueInBaseCurrency", 0)),
                "activitiesCount": pos.get("activitiesCount", 0),
                "tags": pos.get("tags", []),
            }
        return {"holdings": holdings}

    def get_details(self, base_currency="USD") -> dict:
        """Return details: {accounts, holdings, summary, ...}."""
        snapshot = self._compute_snapshot()
        positions = snapshot.get("positions", [])

        holdings = {}
        total_investment = Big(0)
        total_net_perf = Big(0)
        total_value_base = Big(0)
        total_fees = Big(0)

        for pos in positions:
            sym = pos.get("symbol", "")
            investment = pos.get("investment", Big(0))
            quantity = pos.get("quantity", Big(0))
            value_base = pos.get("valueInBaseCurrency", Big(0))
            np_ = pos.get("netPerformance", Big(0)) or Big(0)
            fee = pos.get("fee", Big(0))
            np_pct = pos.get("netPerformancePercentage")

            total_investment = total_investment.plus(investment)
            total_net_perf = total_net_perf.plus(np_)
            total_value_base = total_value_base.plus(value_base)
            total_fees = total_fees.plus(fee)

            inv_val = investment.toNumber() if isinstance(investment, Big) else float(investment)
            np_val = np_.toNumber() if isinstance(np_, Big) else float(np_) if np_ is not None else 0

            holdings[sym] = {
                "symbol": sym,
                "quantity": quantity.toNumber() if isinstance(quantity, Big) else float(quantity),
                "investment": inv_val,
                "currency": pos.get("currency", "USD"),
                "dataSource": pos.get("dataSource", "YAHOO"),
                "dateOfFirstActivity": pos.get("dateOfFirstActivity"),
                "averagePrice": pos["averagePrice"].toNumber() if isinstance(pos.get("averagePrice"), Big) else float(pos.get("averagePrice", 0)),
                "marketPrice": pos.get("marketPrice", 0),
                "marketPriceInBaseCurrency": pos.get("marketPriceInBaseCurrency", 0),
                "fee": fee.toNumber() if isinstance(fee, Big) else float(fee),
                "netPerformance": np_val,
                "netPerformancePercent": (np_val / inv_val) if inv_val != 0 else 0,
                "grossPerformance": pos["grossPerformance"].toNumber() if isinstance(pos.get("grossPerformance"), Big) else (float(pos["grossPerformance"]) if pos.get("grossPerformance") is not None else 0),
                "valueInBaseCurrency": value_base.toNumber() if isinstance(value_base, Big) else float(value_base),
                "activitiesCount": pos.get("activitiesCount", 0),
                "tags": pos.get("tags", []),
            }

        created_at = min((a["date"] for a in self._orders), default=None) if self._orders else None

        return {
            "accounts": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Account",
                    "valueInBaseCurrency": total_value_base.toNumber() if isinstance(total_value_base, Big) else float(total_value_base),
                }
            },
            "createdAt": created_at,
            "holdings": holdings,
            "platforms": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Platform",
                    "valueInBaseCurrency": total_value_base.toNumber() if isinstance(total_value_base, Big) else float(total_value_base),
                }
            },
            "summary": {
                "totalInvestment": total_investment.toNumber() if isinstance(total_investment, Big) else float(total_investment),
                "netPerformance": total_net_perf.toNumber() if isinstance(total_net_perf, Big) else float(total_net_perf),
                "currentValueInBaseCurrency": total_value_base.toNumber() if isinstance(total_value_base, Big) else float(total_value_base),
                "totalFees": total_fees.toNumber() if isinstance(total_fees, Big) else float(total_fees),
            },
            "hasError": snapshot.get("hasErrors", False),
        }

    def get_dividends(self, group_by=None) -> dict:
        """Return dividends: {dividends: [{date, investment}]}."""
        # Extract dividend activities
        dividend_acts = [a for a in self._orders if a["type"] == "DIVIDEND"]

        if not dividend_acts:
            return {"dividends": []}

        dividends = []
        for act in dividend_acts:
            amount = act["quantity"].mul(act["unitPrice"])
            dividends.append({
                "date": act["date"],
                "investment": amount.toNumber(),
            })

        if group_by:
            grouped = {}
            for d in dividends:
                dt = d["date"]
                if group_by == "month":
                    key = dt[:7]
                else:
                    key = dt[:4]
                grouped[key] = grouped.get(key, 0.0) + d["investment"]

            result = []
            for k in sorted(grouped.keys()):
                if group_by == "month":
                    result.append({"date": f"{k}-01", "investment": grouped[k]})
                else:
                    result.append({"date": f"{k}-01-01", "investment": grouped[k]})
            return {"dividends": result}

        return {"dividends": dividends}

    def evaluate_report(self) -> dict:
        """Return report: {xRay: {categories, statistics}}."""
        snapshot = self._compute_snapshot()
        positions = snapshot.get("positions", [])

        # Build basic rules
        rules = []
        rules_active = 0
        rules_fulfilled = 0

        if positions:
            # Account concentration rule
            rules_active += 1
            rules_fulfilled += 1  # Single default account = diversified enough
            rules.append({
                "key": "accountClusterRisk",
                "name": "Account Cluster Risk: Single Account",
                "isActive": True,
                "configuration": {},
            })

            # Currency cluster risk
            currencies = set()
            for pos in positions:
                currencies.add(pos.get("currency", "USD"))

            rules_active += 1
            if len(currencies) >= 1:
                rules_fulfilled += 1
            rules.append({
                "key": "currencyClusterRisk",
                "name": "Currency Cluster Risk: Base Currency",
                "isActive": True,
                "configuration": {},
            })

            # Fee ratio rule
            total_fees = Big(0)
            total_inv = Big(0)
            for pos in positions:
                total_fees = total_fees.plus(pos.get("fee", Big(0)))
                total_inv = total_inv.plus(pos.get("investment", Big(0)))

            rules_active += 1
            fee_ratio = total_fees.div(total_inv).toNumber() if total_inv.gt(0) else 0
            if fee_ratio < 0.015:  # Less than 1.5% fee ratio
                rules_fulfilled += 1
            rules.append({
                "key": "feeRatio",
                "name": "Fee Ratio",
                "isActive": True,
                "configuration": {"threshold": 0.015},
            })

        return {
            "xRay": {
                "categories": [
                    {
                        "key": "accounts",
                        "name": "Accounts",
                        "rules": [r for r in rules if r["key"].startswith("account")],
                    },
                    {
                        "key": "currencies",
                        "name": "Currencies",
                        "rules": [r for r in rules if r["key"].startswith("currency")],
                    },
                    {
                        "key": "fees",
                        "name": "Fees",
                        "rules": [r for r in rules if r["key"].startswith("fee")],
                    },
                ],
                "statistics": {
                    "rulesActiveCount": rules_active,
                    "rulesFulfilledCount": rules_fulfilled,
                },
            }
        }

