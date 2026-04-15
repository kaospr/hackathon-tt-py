"""ROAI Portfolio Calculator — translated from TypeScript."""
from __future__ import annotations

import sys
from copy import deepcopy
from datetime import date, datetime, timedelta

from app.helpers.big import Big, Pair, to_num as _to_num
from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator


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


def _resolve_max_range(today, reference_date):
    """Resolve the max date range."""
    if reference_date is not None:
        return {"startDate": parse_date(reference_date), "endDate": today}
    return {"startDate": sub_years(today, 50), "endDate": today}


def _resolve_year_range(date_range, today):
    """Resolve a year string range like 2021."""
    try:
        year = int(date_range)
        return {"startDate": date(year, 1, 1), "endDate": date(year, 12, 31)}
    except (ValueError, TypeError):
        return {"startDate": sub_years(today, 50), "endDate": today}


def get_interval_from_date_range(date_range, reference_date=None):
    """Return {startDate, endDate} for a named range like '1d', '1y', 'max', etc."""
    today = date.today()
    _RANGE_MAP = {
        "1d": lambda: {"startDate": sub_days(today, 1), "endDate": today},
        "1y": lambda: {"startDate": sub_years(today, 1), "endDate": today},
        "5y": lambda: {"startDate": sub_years(today, 5), "endDate": today},
        "ytd": lambda: {"startDate": start_of_year(today), "endDate": today},
        "mtd": lambda: {"startDate": start_of_month(today), "endDate": today},
        "wtd": lambda: {"startDate": start_of_week(today), "endDate": today},
        "max": lambda: _resolve_max_range(today, reference_date),
    }
    resolver = _RANGE_MAP.get(date_range)
    if resolver:
        return resolver()
    return _resolve_year_range(date_range, today)


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

    @staticmethod
    def _build_symbol_item(old, order, sp, factor):
        """Build or update a transaction point symbol item."""
        symbol = sp["symbol"]
        o_type = order["type"]
        quantity = order["quantity"]
        unit_price = order["unitPrice"]
        base = {
            "assetSubClass": sp.get("assetSubClass"),
            "currency": sp.get("currency", "USD"),
            "dataSource": sp.get("dataSource", "YAHOO"),
            "skipErrors": bool(sp.get("userId")),
            "symbol": symbol,
        }
        if not old:
            return {**base,
                "fee": order["fee"], "feeInBaseCurrency": order["feeInBaseCurrency"],
                "tags": order.get("tags", []), "activitiesCount": 1,
                "averagePrice": unit_price, "dateOfFirstActivity": order["date"],
                "dividend": Big(0),
                "includeInHoldings": o_type in INVESTMENT_ACTIVITY_TYPES,
                "investment": unit_price.mul(quantity).mul(factor),
                "quantity": quantity.mul(factor),
            }

        investment = old["investment"]
        new_quantity = quantity.mul(factor).plus(old["quantity"])

        if o_type == "BUY":
            price = unit_price if old["investment"].gte(0) else old["averagePrice"]
            investment = old["investment"].plus(quantity.mul(price))
        elif o_type == "SELL":
            price = old["averagePrice"] if old["investment"].gt(0) else unit_price
            investment = old["investment"].minus(quantity.mul(price))

        if new_quantity.abs().lt(EPSILON):
            investment = Big(0)
            new_quantity = Big(0)

        return {**base,
            "investment": investment, "activitiesCount": old["activitiesCount"] + 1,
            "averagePrice": Big(0) if new_quantity.eq(0) else investment.div(new_quantity).abs(),
            "dateOfFirstActivity": old["dateOfFirstActivity"], "dividend": Big(0),
            "fee": old["fee"].plus(order["fee"]),
            "feeInBaseCurrency": old["feeInBaseCurrency"].plus(order["feeInBaseCurrency"]),
            "includeInHoldings": old["includeInHoldings"],
            "quantity": new_quantity, "tags": old["tags"] + order.get("tags", []),
        }

    def _compute_transaction_points(self):
        """Build transaction points from orders (mirrors TS computeTransactionPoints)."""
        self._transaction_points = []
        symbols = {}
        last_date = None
        last_tp = None

        for order in self._orders:
            sp = order["SymbolProfile"]
            symbol = sp["symbol"]
            factor = get_factor(order["type"])
            o_date = order["date"]
            o_type = order["type"]
            quantity = order["quantity"]
            unit_price = order["unitPrice"]

            current_item = self._build_symbol_item(symbols.get(symbol), order, sp, factor)
            current_item["tags"] = uniq_by(current_item["tags"], "id")
            symbols[symbol] = current_item

            items = last_tp["items"][:] if last_tp else []
            new_items = [it for it in items if it["symbol"] != symbol]
            new_items.append(current_item)
            new_items.sort(key=lambda a: a.get("symbol", ""))

            fees = order["fee"] if o_type == "FEE" else Big(0)
            interest = quantity.mul(unit_price) if o_type == "INTEREST" else Big(0)
            liabilities = quantity.mul(unit_price) if o_type == "LIABILITY" else Big(0)

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

    @staticmethod
    def _add_date_range_boundaries(chart_date_map, start_date, end_date):
        """Add key date range boundaries and calendar year boundaries."""
        for dr in ["1d", "1y", "5y", "max", "mtd", "wtd", "ytd"]:
            interval = get_interval_from_date_range(dr)
            for boundary in (parse_date(interval["startDate"]), parse_date(interval["endDate"])):
                if not is_before(boundary, start_date) and not is_after(boundary, end_date):
                    chart_date_map[format_date(boundary)] = True

        interval = {"start": start_date, "end": end_date}
        for d in each_year_of_interval(interval):
            for boundary in (start_of_year(d), end_of_year(d)):
                if is_within_interval(boundary, interval):
                    chart_date_map[format_date(boundary)] = True

    def _get_chart_date_map(self, end_date, start_date, step):
        """Build a map of relevant chart dates (mirrors TS getChartDateMap)."""
        chart_date_map = {}

        for tp in self._transaction_points:
            chart_date_map[tp["date"]] = True

        for d in each_day_of_interval({"start": start_date, "end": end_date}, step):
            chart_date_map[format_date(d)] = True

        if step > 1:
            for d in each_day_of_interval({"start": sub_days(end_date, 90), "end": end_date}, 3):
                chart_date_map[format_date(d)] = True
            for d in each_day_of_interval({"start": sub_days(end_date, 30), "end": end_date}, 1):
                chart_date_map[format_date(d)] = True

        chart_date_map[format_date(end_date)] = True
        self._add_date_range_boundaries(chart_date_map, start_date, end_date)
        return chart_date_map

    def _ensure_today_prices(self, market_symbol_map, symbols):
        """Ensure today has price data using nearest/latest prices."""
        today_str = format_date(date.today())
        if today_str not in market_symbol_map:
            market_symbol_map[today_str] = {}
        for sym in symbols:
            if sym not in market_symbol_map[today_str]:
                latest = self.current_rate_service.get_latest_price(sym)
                if latest and latest > 0:
                    market_symbol_map[today_str][sym] = Big(latest)

    def _fetch_symbol_prices(self, all_dates, symbols):
        """Build market symbol map from price data."""
        market_symbol_map = {}
        for date_str in sorted(all_dates):
            market_symbol_map[date_str] = {}
            for sym in symbols:
                price = self.current_rate_service.get_price(sym, date_str)
                if price is not None:
                    market_symbol_map[date_str][sym] = Big(price)
        return market_symbol_map

    def _build_market_data(self):
        """Build marketSymbolMap and exchangeRates from current_rate_service."""
        if not self._transaction_points:
            return {}, {}

        last_tp = self._transaction_points[-1]
        symbols = [item["symbol"] for item in last_tp["items"] if item.get("assetSubClass") != "CASH"]

        all_dates = self.current_rate_service.all_dates_in_range(
            format_date(self._start_date), format_date(self._end_date),
        )
        for tp in self._transaction_points:
            all_dates.add(tp["date"])

        market_symbol_map = self._fetch_symbol_prices(all_dates, symbols)
        self._ensure_today_prices(market_symbol_map, symbols)

        today_str = format_date(date.today())
        exchange_rates = {d: 1.0 for d in all_dates}
        exchange_rates[today_str] = 1.0
        return market_symbol_map, exchange_rates

    @staticmethod
    def _empty_metrics(has_errors=False):
        """Return empty/zero metrics dict."""
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

    def _enrich_chart_date_orders(self, orders, orders_by_date, start_date_string, end_date_string, data_source, symbol, is_cash, market_symbol_map, chart_date_map):
        """Add chart-date orders and enrich with market prices."""
        last_unit_price = None
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
                    "date": date_string, "fee": Big(0), "feeInBaseCurrency": Big(0),
                    "quantity": Big(0),
                    "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": "CASH" if is_cash else None},
                    "type": "BUY", "unitPrice": market_price, "unitPriceFromMarketData": market_price, "tags": [],
                })
            latest_activity = orders[-1]
            last_unit_price = latest_activity.get("unitPriceFromMarketData") or latest_activity.get("unitPrice")

    def _prepare_symbol_orders(self, orders, chart_date_map, data_source, symbol, is_cash, start_date_string, end_date_string, market_symbol_map):
        """Add synthetic and chart-date orders, then sort them."""
        unit_price_at_start = market_symbol_map.get(start_date_string, {}).get(symbol)
        unit_price_at_end = market_symbol_map.get(end_date_string, {}).get(symbol)

        orders.append({
            "date": start_date_string, "fee": Big(0), "feeInBaseCurrency": Big(0),
            "itemType": "start", "quantity": Big(0),
            "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": "CASH" if is_cash else None},
            "type": "BUY", "unitPrice": unit_price_at_start, "tags": [],
        })
        orders.append({
            "date": end_date_string, "fee": Big(0), "feeInBaseCurrency": Big(0),
            "itemType": "end",
            "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": "CASH" if is_cash else None},
            "quantity": Big(0), "type": "BUY", "unitPrice": unit_price_at_end, "tags": [],
        })

        orders_by_date = {}
        for o in orders:
            orders_by_date.setdefault(o["date"], []).append(o)

        self._enrich_chart_date_orders(orders, orders_by_date, start_date_string, end_date_string, data_source, symbol, is_cash, market_symbol_map, chart_date_map)

        def sort_key(o):
            d = parse_date(o["date"])
            item_type = o.get("itemType")
            if item_type == "end":
                return (d, 1)
            elif item_type == "start":
                return (d, -1)
            return (d, 0)

        return sorted(orders, key=sort_key)

    @staticmethod
    def _compute_txn_investment(order, total_inv, total_units):
        """Compute transaction investment for a BUY or SELL order."""
        if order["type"] == "BUY":
            f = get_factor(order["type"])
            return Pair(
                order["quantity"].mul(order.get("unitPriceInBaseCurrency", Big(0))).mul(f),
                order["quantity"].mul(order.get("unitPriceInBaseCurrencyWithCurrencyEffect", Big(0))).mul(f),
            )
        if order["type"] == "SELL" and total_units.gt(0):
            f = get_factor(order["type"])
            return Pair(
                total_inv.base.div(total_units).mul(order["quantity"]).mul(f),
                total_inv.ce.div(total_units).mul(order["quantity"]).mul(f),
            )
        return Pair.zero()

    @staticmethod
    def _enrich_order_prices(order, current_exchange_rate, ex_rate):
        """Set base-currency price fields on an order."""
        if order.get("fee"):
            order["feeInBaseCurrency"] = order["fee"].mul(current_exchange_rate)
            order["feeInBaseCurrencyWithCurrencyEffect"] = order["fee"].mul(ex_rate)
        up = order.get("unitPrice") if order["type"] in ("BUY", "SELL") else order.get("unitPriceFromMarketData")
        if up:
            order["unitPriceInBaseCurrency"] = up.mul(current_exchange_rate)
            order["unitPriceInBaseCurrencyWithCurrencyEffect"] = up.mul(ex_rate)

    def _record_date_values(self, s, order, val_of_inv, gross_perf, fees, txn_inv, orders, i):
        """Record per-date values for dates after start."""
        d = order["date"]
        val_before = s["val_before"]
        if val_before.base.gt(0) and order["type"] in ("BUY", "SELL"):
            days_since = difference_in_days(parse_date(d), parse_date(orders[i - 1]["date"]))
            if days_since <= 0:
                days_since = EPSILON
            s["total_investment_days"] += days_since
            s["sum_twi"] = Pair(
                s["sum_twi"].base.add(s["val_at_start"].base.minus(s["inv_at_start"].base).plus(s["total_inv_before"].base).mul(days_since)),
                s["sum_twi"].ce.add(s["val_at_start"].ce.minus(s["inv_at_start"].ce).plus(s["total_inv_before"].ce).mul(days_since)),
            )

        s["current_values"][d] = val_of_inv.base
        s["current_values_ce"][d] = val_of_inv.ce
        s["net_perf_values"][d] = gross_perf.base.minus(s["gross_perf_at_start"].base).minus(fees.base.minus(s["fees_at_start"].base))
        s["net_perf_values_ce"][d] = gross_perf.ce.minus(s["gross_perf_at_start"].ce).minus(fees.ce.minus(s["fees_at_start"].ce))
        s["inv_values_acc"][d] = s["total_inv"].base
        s["inv_values_acc_ce"][d] = s["total_inv"].ce
        s["inv_values_ce"][d] = s["inv_values_ce"].get(d, Big(0)).add(txn_inv.ce)

        tid = s["total_investment_days"]
        ti = s["total_inv"]
        stw = s["sum_twi"]
        s["twi_values"][d] = stw.base.div(tid) if tid > EPSILON else (ti.base if ti.base.gt(0) else Big(0))
        s["twi_values_ce"][d] = stw.ce.div(tid) if tid > EPSILON else (ti.ce if ti.ce.gt(0) else Big(0))

    @staticmethod
    def _accumulate_income(s, order, ex_rate, income_keys_map):
        """Process income accumulation for DIVIDEND/INTEREST/LIABILITY."""
        income_keys = income_keys_map.get(order["type"])
        if income_keys:
            amt = order["quantity"].mul(order["unitPrice"])
            s[income_keys[0]] = s[income_keys[0]].plus(amt)
            s[income_keys[1]] = s[income_keys[1]].plus(amt.mul(ex_rate))

    @staticmethod
    def _compute_sell_gp(order, last_avg_price):
        """Compute gross performance from a sell order."""
        if order["type"] != "SELL":
            return Pair.zero()
        return Pair(
            order.get("unitPriceInBaseCurrency", Big(0)).minus(last_avg_price.base).mul(order["quantity"]),
            order.get("unitPriceInBaseCurrencyWithCurrencyEffect", Big(0)).minus(last_avg_price.ce).mul(order["quantity"]),
        )

    @staticmethod
    def _resolve_initial_value(s, i, index_of_start, txn_inv):
        """Resolve the initial value at start."""
        if i < index_of_start or s["initial_value"].base:
            return
        if i == index_of_start and not s["val_before"].base.eq(0):
            s["initial_value"] = s["val_before"]
        elif txn_inv.base.gt(0):
            s["initial_value"] = txn_inv

    @staticmethod
    def _update_avg_price(s, txn_inv):
        """Compute average price and reset on zero units."""
        if s["total_quantity_from_buys"].eq(0):
            s["last_avg_price"] = Pair.zero()
        else:
            s["last_avg_price"] = s["total_inv_from_buys"].div_each(s["total_quantity_from_buys"])
        if s["total_units"].eq(0):
            s["total_inv_from_buys"] = Pair.zero()
            s["total_quantity_from_buys"] = Big(0)

    @staticmethod
    def _init_start_tracking(s, i, index_of_start):
        """Set inv_at_start and val_at_start on first eligible order."""
        if s["inv_at_start"].base is None and i >= index_of_start:
            s["inv_at_start"] = Pair(s["total_inv"].base or Big(0), s["total_inv"].ce or Big(0))
            s["val_at_start"] = s["val_before"]

    @staticmethod
    def _track_buy(s, order, txn_inv):
        """Process BUY order accumulation."""
        if order["type"] == "BUY":
            s["total_quantity_from_buys"] = s["total_quantity_from_buys"].plus(order["quantity"])
            s["total_inv_from_buys"] = s["total_inv_from_buys"].plus(txn_inv)

    def _process_orders_loop(self, orders, index_of_start, index_of_end, exchange_rates, current_exchange_rate, unit_price_at_start):
        """Process all orders and compute running totals using Pair for base/ce values."""
        s = {
            "fees": Pair.zero(), "fees_at_start": Pair.zero(),
            "gross_perf": Pair.zero(), "gross_perf_at_start": Pair.zero(),
            "gp_from_sells": Pair.zero(), "initial_value": Pair(None, None),
            "inv_at_start": Pair(None, None), "val_at_start": Pair(None, None),
            "last_avg_price": Pair.zero(), "total_inv": Pair.zero(),
            "total_inv_from_buys": Pair.zero(), "sum_twi": Pair.zero(),
            "total_inv_before": Pair.zero(), "val_before": Pair.zero(),
            "current_values": {}, "current_values_ce": {},
            "inv_values_acc": {}, "inv_values_acc_ce": {}, "inv_values_ce": {},
            "net_perf_values": {}, "net_perf_values_ce": {},
            "twi_values": {}, "twi_values_ce": {},
            "total_dividend": Big(0), "total_dividend_in_base": Big(0),
            "total_interest": Big(0), "total_interest_in_base": Big(0),
            "total_liabilities": Big(0), "total_liabilities_in_base": Big(0),
            "total_quantity_from_buys": Big(0), "total_units": Big(0),
            "total_investment_days": 0,
        }
        _INCOME_KEYS = {"DIVIDEND": ("total_dividend", "total_dividend_in_base"),
                        "INTEREST": ("total_interest", "total_interest_in_base"),
                        "LIABILITY": ("total_liabilities", "total_liabilities_in_base")}

        for i, order in enumerate(orders):
            ex_rate = exchange_rates.get(order["date"], 1)

            self._accumulate_income(s, order, ex_rate, _INCOME_KEYS)

            if order.get("itemType") == "start":
                order["unitPrice"] = (
                    orders[i + 1]["unitPrice"] if index_of_start == 0 and i + 1 < len(orders)
                    else unit_price_at_start
                )

            self._enrich_order_prices(order, current_exchange_rate, ex_rate)

            raw_market = order.get("unitPriceFromMarketData", Big(0)) or Big(0)
            market_price = Pair(raw_market.mul(current_exchange_rate), raw_market.mul(ex_rate))
            s["val_before"] = Pair(s["total_units"].mul(market_price.base), s["total_units"].mul(market_price.ce))

            self._init_start_tracking(s, i, index_of_start)

            txn_inv = self._compute_txn_investment(order, s["total_inv"], s["total_units"])
            self._track_buy(s, order, txn_inv)

            s["total_inv_before"] = Pair(s["total_inv"].base, s["total_inv"].ce)
            s["total_inv"] = s["total_inv"].plus(txn_inv)

            self._resolve_initial_value(s, i, index_of_start, txn_inv)

            s["fees"] = s["fees"].plus(Pair(
                order.get("feeInBaseCurrency") or Big(0),
                order.get("feeInBaseCurrencyWithCurrencyEffect") or Big(0),
            ))

            s["total_units"] = s["total_units"].plus(order["quantity"].mul(get_factor(order["type"])))
            val_of_inv = Pair(s["total_units"].mul(market_price.base), s["total_units"].mul(market_price.ce))

            gp_sell = self._compute_sell_gp(order, s["last_avg_price"])
            s["gp_from_sells"] = s["gp_from_sells"].plus(gp_sell)

            self._update_avg_price(s, txn_inv)

            s["gross_perf"] = Pair(
                val_of_inv.base.minus(s["total_inv"].base).plus(s["gp_from_sells"].base),
                val_of_inv.ce.minus(s["total_inv"].ce).plus(s["gp_from_sells"].ce),
            )

            if order.get("itemType") == "start":
                s["fees_at_start"] = Pair(s["fees"].base, s["fees"].ce)
                s["gross_perf_at_start"] = Pair(s["gross_perf"].base, s["gross_perf"].ce)

            if i > index_of_start:
                self._record_date_values(s, order, val_of_inv, s["gross_perf"], s["fees"], txn_inv, orders, i)

            if i == index_of_end:
                break

        return {
            "fees": s["fees"], "fees_at_start": s["fees_at_start"],
            "gross_perf": s["gross_perf"], "gross_perf_at_start": s["gross_perf_at_start"],
            "initial_value": s["initial_value"], "total_inv": s["total_inv"],
            "sum_twi": s["sum_twi"], "total_investment_days": s["total_investment_days"],
            "total_units": s["total_units"],
            "current_values": s["current_values"], "current_values_ce": s["current_values_ce"],
            "inv_values_acc": s["inv_values_acc"], "inv_values_acc_ce": s["inv_values_acc_ce"],
            "inv_values_ce": s["inv_values_ce"],
            "net_perf_values": s["net_perf_values"], "net_perf_values_ce": s["net_perf_values_ce"],
            "twi_values": s["twi_values"], "twi_values_ce": s["twi_values_ce"],
            "total_dividend": s["total_dividend"], "total_dividend_in_base": s["total_dividend_in_base"],
            "total_interest": s["total_interest"], "total_interest_in_base": s["total_interest_in_base"],
            "total_liabilities": s["total_liabilities"], "total_liabilities_in_base": s["total_liabilities_in_base"],
            "unit_price_at_end": orders[next((i for i, o in enumerate(orders) if o.get("itemType") == "end"), len(orders) - 1)].get("unitPrice"),
        }

    @staticmethod
    def _compute_range_average(chart_dates, inv_values_acc_ce, gp_at_start_ce, range_start_str, range_end_str):
        """Compute average investment for a date range."""
        average = Big(0)
        day_count = 0
        for j in range(len(chart_dates) - 1, -1, -1):
            d = chart_dates[j]
            if d > range_end_str:
                continue
            elif d < range_start_str:
                break
            acc_val = inv_values_acc_ce.get(d)
            if acc_val is not None and isinstance(acc_val, Big) and acc_val.gt(0):
                average = average.add(acc_val.add(gp_at_start_ce))
                day_count += 1
        return average.div(day_count) if day_count > 0 else average

    def _compute_date_range_performance(self, start, end, current_values_ce, inv_values_acc_ce, net_perf_values_ce):
        """Compute per-dateRange net performance maps."""
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

            cv_at_start_ce = current_values_ce.get(range_start_str, Big(0))
            iv_acc_at_start_ce = inv_values_acc_ce.get(range_start_str, Big(0))
            gp_at_start_ce = cv_at_start_ce.minus(iv_acc_at_start_ce)

            average = self._compute_range_average(self._chart_dates, inv_values_acc_ce, gp_at_start_ce, range_start_str, range_end_str)

            end_val = net_perf_values_ce.get(range_end_str, Big(0))
            start_val = Big(0) if dr == "max" else net_perf_values_ce.get(range_start_str, Big(0))
            np_with_ce_map[dr] = end_val.minus(start_val)
            np_pct_ce_map[dr] = np_with_ce_map[dr].div(average) if average.gt(0) else Big(0)

        return np_pct_ce_map, np_with_ce_map

    def _build_symbol_metrics_result(self, loop_result, start, end, gp_pct, gp_pct_ce, np_pct, np_pct_ce_map, np_with_ce_map, twi_avg):
        """Assemble the final metrics dict from loop results."""
        r = loop_result
        iv = r["initial_value"]
        return {
            "currentValues": r["current_values"],
            "currentValuesWithCurrencyEffect": r["current_values_ce"],
            "feesWithCurrencyEffect": r["fees"].ce,
            "grossPerformancePercentage": gp_pct,
            "grossPerformancePercentageWithCurrencyEffect": gp_pct_ce,
            "initialValue": iv.base if iv.base else Big(0),
            "initialValueWithCurrencyEffect": iv.ce if iv.ce else Big(0),
            "investmentValuesAccumulated": r["inv_values_acc"],
            "investmentValuesAccumulatedWithCurrencyEffect": r["inv_values_acc_ce"],
            "investmentValuesWithCurrencyEffect": r["inv_values_ce"],
            "netPerformancePercentage": np_pct,
            "netPerformancePercentageWithCurrencyEffectMap": np_pct_ce_map,
            "netPerformanceValues": r["net_perf_values"],
            "netPerformanceValuesWithCurrencyEffect": r["net_perf_values_ce"],
            "netPerformanceWithCurrencyEffectMap": np_with_ce_map,
            "timeWeightedInvestmentValues": r["twi_values"],
            "timeWeightedInvestmentValuesWithCurrencyEffect": r["twi_values_ce"],
            "totalAccountBalanceInBaseCurrency": Big(0),
            "totalDividend": r["total_dividend"],
            "totalDividendInBaseCurrency": r["total_dividend_in_base"],
            "totalInterest": r["total_interest"],
            "totalInterestInBaseCurrency": r["total_interest_in_base"],
            "totalInvestment": r["total_inv"].base,
            "totalInvestmentWithCurrencyEffect": r["total_inv"].ce,
            "totalLiabilities": r["total_liabilities"],
            "totalLiabilitiesInBaseCurrency": r["total_liabilities_in_base"],
            "grossPerformance": r["gross_perf"].base.minus(r["gross_perf_at_start"].base),
            "grossPerformanceWithCurrencyEffect": r["gross_perf"].ce.minus(r["gross_perf_at_start"].ce),
            "hasErrors": r["total_units"].gt(0) and (not iv.base or not r["unit_price_at_end"]),
            "netPerformance": r["gross_perf"].base.minus(r["gross_perf_at_start"].base).minus(
                r["fees"].base.minus(r["fees_at_start"].base)
            ),
            "timeWeightedInvestment": twi_avg.base,
            "timeWeightedInvestmentWithCurrencyEffect": twi_avg.ce,
        }

    def _get_symbol_metrics(self, chart_date_map, data_source, end, exchange_rates, market_symbol_map, start, symbol):
        """Calculate per-symbol metrics (mirrors TS getSymbolMetrics -- ROAI variant)."""
        current_exchange_rate = exchange_rates.get(format_date(date.today()), 1)

        orders = clone_deep([o for o in self._orders if o["SymbolProfile"]["symbol"] == symbol])
        is_cash = (orders[0]["SymbolProfile"].get("assetSubClass") == "CASH") if orders else False

        if len(orders) <= 0:
            return self._empty_metrics()

        date_of_first_transaction = parse_date(orders[0]["date"])
        end_date_string = format_date(end)
        start_date_string = format_date(start)

        unit_price_at_start = market_symbol_map.get(start_date_string, {}).get(symbol)
        unit_price_at_end = market_symbol_map.get(end_date_string, {}).get(symbol)
        latest_activity = orders[-1] if orders else None

        if (data_source == "MANUAL"
            and latest_activity and latest_activity.get("type") in ("BUY", "SELL")
            and latest_activity.get("unitPrice") and not unit_price_at_end):
            unit_price_at_end = latest_activity["unitPrice"]
        elif is_cash:
            unit_price_at_end = Big(1)

        if (not unit_price_at_end or
            (not unit_price_at_start and is_before(date_of_first_transaction, start))):
            return self._empty_metrics(has_errors=True)

        orders = self._prepare_symbol_orders(
            orders, chart_date_map, data_source, symbol, is_cash,
            start_date_string, end_date_string, market_symbol_map,
        )

        index_of_start = next((i for i, o in enumerate(orders) if o.get("itemType") == "start"), 0)
        index_of_end = next((i for i, o in enumerate(orders) if o.get("itemType") == "end"), len(orders) - 1)

        r = self._process_orders_loop(
            orders, index_of_start, index_of_end,
            exchange_rates, current_exchange_rate, unit_price_at_start,
        )

        total_gp = Pair(
            r["gross_perf"].base.minus(r["gross_perf_at_start"].base),
            r["gross_perf"].ce.minus(r["gross_perf_at_start"].ce),
        )
        total_np = total_gp.base.minus(r["fees"].base.minus(r["fees_at_start"].base))

        days = r["total_investment_days"]
        twi_avg = Pair(
            r["sum_twi"].base.div(days) if days > 0 else Big(0),
            r["sum_twi"].ce.div(days) if days > 0 else Big(0),
        )

        gp_pct = total_gp.base.div(twi_avg.base) if twi_avg.base.gt(0) else Big(0)
        gp_pct_ce = total_gp.ce.div(twi_avg.ce) if twi_avg.ce.gt(0) else Big(0)
        np_pct = total_np.div(twi_avg.base) if twi_avg.base.gt(0) else Big(0)

        np_pct_ce_map, np_with_ce_map = self._compute_date_range_performance(
            start, end, r["current_values_ce"], r["inv_values_acc_ce"], r["net_perf_values_ce"],
        )

        return self._build_symbol_metrics_result(
            r, start, end, gp_pct, gp_pct_ce, np_pct, np_pct_ce_map, np_with_ce_map, twi_avg,
        )


    @staticmethod
    def _accumulate_position_perf(acc, pos):
        """Aggregate performance and time-weighted investment from a position."""
        if pos.get("grossPerformance"):
            acc["gp"] = acc["gp"].plus(pos["grossPerformance"])
            acc["gp_ce"] = acc["gp_ce"].plus(pos.get("grossPerformanceWithCurrencyEffect", Big(0)))
            acc["np_"] = acc["np_"].plus(pos.get("netPerformance", Big(0)))
        elif not pos.get("quantity", Big(0)).eq(0):
            acc["has_errors"] = True
        if pos.get("timeWeightedInvestment"):
            acc["total_twi"] = acc["total_twi"].plus(pos["timeWeightedInvestment"])
            acc["total_twi_ce"] = acc["total_twi_ce"].plus(pos.get("timeWeightedInvestmentWithCurrencyEffect", Big(0)))
        elif not pos.get("quantity", Big(0)).eq(0):
            acc["has_errors"] = True

    @staticmethod
    def _accumulate_position(acc, pos):
        """Aggregate a single position into accumulator."""
        if pos.get("feeInBaseCurrency"):
            acc["total_fees_ce"] = acc["total_fees_ce"].plus(pos["feeInBaseCurrency"])
        if pos.get("valueInBaseCurrency"):
            acc["cv_base"] = acc["cv_base"].plus(pos["valueInBaseCurrency"])
        else:
            acc["has_errors"] = True
        if pos.get("investment"):
            acc["total_inv"] = acc["total_inv"].plus(pos["investment"])
            acc["total_inv_ce"] = acc["total_inv_ce"].plus(pos.get("investmentWithCurrencyEffect", pos["investment"]))
        else:
            acc["has_errors"] = True
        RoaiPortfolioCalculator._accumulate_position_perf(acc, pos)

    def _calculate_overall_performance(self, positions):
        """Aggregate position-level metrics into portfolio snapshot (mirrors TS calculateOverallPerformance)."""
        acc = {"cv_base": Big(0), "gp": Big(0), "gp_ce": Big(0), "has_errors": False,
            "np_": Big(0), "total_fees_ce": Big(0), "total_inv": Big(0),
            "total_inv_ce": Big(0), "total_twi": Big(0), "total_twi_ce": Big(0)}

        for pos in positions:
            if pos.get("includeInTotalAssetValue", True):
                self._accumulate_position(acc, pos)

        return {
            "currentValueInBaseCurrency": acc["cv_base"],
            "hasErrors": acc["has_errors"],
            "positions": positions,
            "totalFeesWithCurrencyEffect": acc["total_fees_ce"],
            "totalInterestWithCurrencyEffect": Big(0),
            "totalInvestment": acc["total_inv"],
            "totalInvestmentWithCurrencyEffect": acc["total_inv_ce"],
            "activitiesCount": len([
                o for o in self._orders if o["type"] in ("BUY", "SELL")
            ]),
            "createdAt": datetime.now(),
            "errors": [],
            "historicalData": [],
            "totalLiabilitiesWithCurrencyEffect": Big(0),
        }

    def _build_positions(self, last_tp, end_date_string, chart_date_map, exchange_rates, market_symbol_map):
        """Build position list and collect per-symbol date-series data."""
        errors = []
        has_any_errors = False
        positions = []
        values_by_symbol = {}
        total_interest_ce = Big(0)
        total_liabilities_ce = Big(0)

        for item in last_tp["items"]:
            market_price_base = (
                market_symbol_map.get(end_date_string, {}).get(item["symbol"])
                or item.get("averagePrice", Big(0))
            )
            market_price_in_base = market_price_base

            metrics = self._get_symbol_metrics(
                chart_date_map=chart_date_map, data_source=item["dataSource"],
                end=self._end_date, exchange_rates=exchange_rates,
                market_symbol_map=market_symbol_map, start=self._start_date,
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
            has_err = metrics["hasErrors"]

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
                "grossPerformance": metrics["grossPerformance"] if not has_err else None,
                "grossPerformancePercentage": metrics["grossPerformancePercentage"] if not has_err else None,
                "grossPerformancePercentageWithCurrencyEffect": metrics["grossPerformancePercentageWithCurrencyEffect"] if not has_err else None,
                "grossPerformanceWithCurrencyEffect": metrics["grossPerformanceWithCurrencyEffect"] if not has_err else None,
                "includeInHoldings": item.get("includeInHoldings", True),
                "investment": metrics["totalInvestment"],
                "investmentWithCurrencyEffect": metrics["totalInvestmentWithCurrencyEffect"],
                "marketPrice": market_symbol_map.get(end_date_string, {}).get(item["symbol"], Big(1)).toNumber(),
                "marketPriceInBaseCurrency": _to_num(market_price_in_base),
                "netPerformance": metrics["netPerformance"] if not has_err else None,
                "netPerformancePercentage": metrics["netPerformancePercentage"] if not has_err else None,
                "netPerformancePercentageWithCurrencyEffectMap": metrics["netPerformancePercentageWithCurrencyEffectMap"] if not has_err else None,
                "netPerformanceWithCurrencyEffectMap": metrics["netPerformanceWithCurrencyEffectMap"] if not has_err else None,
                "quantity": item["quantity"],
                "symbol": item["symbol"],
                "tags": item.get("tags", []),
                "valueInBaseCurrency": value_in_base,
            })

            total_interest_ce = total_interest_ce.plus(metrics.get("totalInterestInBaseCurrency", Big(0)))
            total_liabilities_ce = total_liabilities_ce.plus(metrics.get("totalLiabilitiesInBaseCurrency", Big(0)))

            if has_err and item.get("investment", Big(0)).gt(0) and not item.get("skipErrors", False):
                errors.append({"dataSource": item["dataSource"], "symbol": item["symbol"]})

        return positions, values_by_symbol, errors, has_any_errors, total_interest_ce, total_liabilities_ce

    def _build_historical_data(self, chart_dates, values_by_symbol):
        """Aggregate per-symbol values into historical data entries."""
        accumulated = {}
        _ZERO_ACC = lambda: {
            "investmentValueWithCurrencyEffect": Big(0),
            "totalAccountBalanceWithCurrencyEffect": Big(0),
            "totalCurrentValue": Big(0), "totalCurrentValueWithCurrencyEffect": Big(0),
            "totalInvestmentValue": Big(0), "totalInvestmentValueWithCurrencyEffect": Big(0),
            "totalNetPerformanceValue": Big(0), "totalNetPerformanceValueWithCurrencyEffect": Big(0),
            "totalTimeWeightedInvestmentValue": Big(0), "totalTimeWeightedInvestmentValueWithCurrencyEffect": Big(0),
        }

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

                if date_string not in accumulated:
                    accumulated[date_string] = _ZERO_ACC()

                acc = accumulated[date_string]
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
        for d in sorted(accumulated.keys()):
            vals = accumulated[d]
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
                "netWorth": vals["totalCurrentValueWithCurrencyEffect"].plus(vals["totalAccountBalanceWithCurrencyEffect"]).toNumber(),
                "totalAccountBalance": vals["totalAccountBalanceWithCurrencyEffect"].toNumber(),
                "totalInvestment": vals["totalInvestmentValue"].toNumber(),
                "totalInvestmentValueWithCurrencyEffect": vals["totalInvestmentValueWithCurrencyEffect"].toNumber(),
                "value": vals["totalCurrentValue"].toNumber(),
                "valueWithCurrencyEffect": vals["totalCurrentValueWithCurrencyEffect"].toNumber(),
            })
        return historical_data

    @staticmethod
    def _empty_snapshot():
        """Return empty snapshot with zero values."""
        return {
            "activitiesCount": 0, "createdAt": datetime.now(),
            "currentValueInBaseCurrency": Big(0), "errors": [], "hasErrors": False,
            "historicalData": [], "positions": [],
            "totalFeesWithCurrencyEffect": Big(0), "totalInterestWithCurrencyEffect": Big(0),
            "totalInvestment": Big(0), "totalInvestmentWithCurrencyEffect": Big(0),
            "totalLiabilitiesWithCurrencyEffect": Big(0),
        }

    @staticmethod
    def _find_first_tp_index(transaction_points, start_date):
        """Compute the first transaction point index for snapshot."""
        first_index = len(transaction_points)
        for i, tp in enumerate(transaction_points):
            if not is_before(parse_date(tp["date"]), start_date):
                first_index = i
                break
        return max(0, first_index - 1) if first_index > 0 else 0

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
            self._snapshot_cache = self._empty_snapshot()
            return self._snapshot_cache

        market_symbol_map, exchange_rates = self._build_market_data()

        first_index = self._find_first_tp_index(transaction_points, self._start_date)

        end_date_string = format_date(self._end_date)
        days_in_market = difference_in_days(self._end_date, self._start_date)
        step = max(1, round(days_in_market / min(days_in_market, 500))) if days_in_market > 0 else 1

        chart_date_map = self._get_chart_date_map(end_date=self._end_date, start_date=self._start_date, step=step)
        chart_dates = sorted(chart_date_map.keys())

        positions, values_by_symbol, errors, has_any_errors, total_interest_ce, total_liabilities_ce = (
            self._build_positions(last_tp, end_date_string, chart_date_map, exchange_rates, market_symbol_map)
        )

        historical_data = self._build_historical_data(chart_dates, values_by_symbol)
        overall = self._calculate_overall_performance(positions)

        positions_for_holdings = [
            {k: v for k, v in p.items() if k != "includeInHoldings"}
            for p in positions if p.get("includeInHoldings", True)
        ]

        result = {
            **overall, "errors": errors, "historicalData": historical_data,
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

    def _build_chart(self, historical_data):
        """Build chart entries from historical data."""
        chart = []
        np_at_start = None
        np_ce_at_start = None
        total_inv_vals_ce = []
        start = self._start_date
        end = self._end_date

        for item in historical_data:
            d = parse_date(item["date"])
            if is_before(d, start) or is_after(d, end):
                continue
            if np_at_start is None:
                np_at_start = item["netPerformance"]
                np_ce_at_start = item["netPerformanceWithCurrencyEffect"]

            np_since = item["netPerformance"] - np_at_start
            np_ce_since = item["netPerformanceWithCurrencyEffect"] - np_ce_at_start

            if item.get("totalInvestmentValueWithCurrencyEffect", 0) > 0:
                total_inv_vals_ce.append(item["totalInvestmentValueWithCurrencyEffect"])

            twi_val = (sum(total_inv_vals_ce) / len(total_inv_vals_ce)) if total_inv_vals_ce else 0

            entry = dict(item)
            entry["netPerformance"] = np_since
            entry["netPerformanceWithCurrencyEffect"] = np_ce_since
            entry["netPerformanceInPercentage"] = 0 if twi_val == 0 else np_since / twi_val
            entry["netPerformanceInPercentageWithCurrencyEffect"] = 0 if twi_val == 0 else np_ce_since / twi_val
            chart.append(entry)
        return chart

    @staticmethod
    def _extract_np_pct_from_pos(pos):
        """Extract net performance percentage from a position."""
        pos_np_pct = pos.get("netPerformancePercentage")
        if pos_np_pct is not None and isinstance(pos_np_pct, Big) and not pos_np_pct.eq(0):
            return pos_np_pct.toNumber()
        np_pct_map = pos.get("netPerformancePercentageWithCurrencyEffectMap")
        if isinstance(np_pct_map, dict):
            max_pct = np_pct_map.get("max", Big(0))
            if isinstance(max_pct, Big) and not max_pct.eq(0):
                return max_pct.toNumber()
        return None

    @staticmethod
    def _fallback_np_pct(positions, total_np, total_np_pct, total_np_pct_ce):
        """Resolve net performance percentages from positions when chart gives 0."""
        if (total_np_pct != 0 and total_np_pct_ce != 0) or total_np.eq(0):
            return total_np_pct, total_np_pct_ce
        for pos in positions:
            val = RoaiPortfolioCalculator._extract_np_pct_from_pos(pos)
            if val is not None:
                total_np_pct = total_np_pct or val
                total_np_pct_ce = total_np_pct_ce or val
        return total_np_pct, total_np_pct_ce

    def get_performance(self) -> dict:
        """Return full performance response: {chart, firstOrderDate, performance}."""
        snapshot = self._compute_snapshot()
        chart = self._build_chart(snapshot.get("historicalData", []))
        positions = snapshot.get("positions", [])

        total_np = Big(0)
        total_np_ce = Big(0)
        for pos in positions:
            if pos.get("netPerformance") is not None:
                total_np = total_np.plus(pos["netPerformance"])
            np_ce_map = pos.get("netPerformanceWithCurrencyEffectMap")
            if isinstance(np_ce_map, dict):
                total_np_ce = total_np_ce.plus(np_ce_map.get("max", Big(0)))

        total_np_pct = chart[-1].get("netPerformanceInPercentage", 0) if chart else 0
        total_np_pct_ce = chart[-1].get("netPerformanceInPercentageWithCurrencyEffect", 0) if chart else 0
        total_np_pct, total_np_pct_ce = self._fallback_np_pct(positions, total_np, total_np_pct, total_np_pct_ce)

        cv_num = _to_num(snapshot.get("currentValueInBaseCurrency", Big(0)))
        perf = {
            "currentNetWorth": cv_num, "currentValue": cv_num, "currentValueInBaseCurrency": cv_num,
            "netPerformance": _to_num(total_np),
            "netPerformancePercentage": _to_num(total_np_pct),
            "netPerformancePercentageWithCurrencyEffect": _to_num(total_np_pct_ce),
            "netPerformanceWithCurrencyEffect": _to_num(total_np_ce),
            "totalFees": _to_num(snapshot.get("totalFeesWithCurrencyEffect", Big(0))),
            "totalInvestment": _to_num(snapshot.get("totalInvestment", Big(0))),
            "totalLiabilities": _to_num(snapshot.get("totalLiabilitiesWithCurrencyEffect", Big(0))),
            "totalValueables": 0.0,
        }

        first_order_date = min((a["date"] for a in self._orders), default=None) if self._orders else None
        return {"chart": chart, "firstOrderDate": first_order_date, "performance": perf}

    @staticmethod
    def _build_delta_map(historical_data):
        """Build investment delta map from historical data."""
        delta_map = {}
        for item in historical_data:
            inv_val = item.get("investmentValueWithCurrencyEffect", 0)
            if inv_val and inv_val != 0:
                delta_map[item["date"]] = inv_val if isinstance(inv_val, (int, float)) else float(inv_val)
        return delta_map

    @staticmethod
    def _tp_investment(tp):
        """Compute total investment for a transaction point."""
        total = Big(0)
        for item in tp["items"]:
            total = total.plus(item["investment"])
        return total.toNumber()

    def get_investments(self, group_by=None) -> dict:
        """Return investments: {investments: [{date, investment}]}."""
        snapshot = self._compute_snapshot()
        historical_data = snapshot.get("historicalData", [])
        if group_by:
            return {"investments": self.get_investments_by_group(historical_data, group_by)}
        delta_map = self._build_delta_map(historical_data)
        investments = []
        for tp in self._transaction_points:
            d = tp["date"]
            inv = delta_map[d] if d in delta_map else self._tp_investment(tp)
            investments.append({"date": d, "investment": inv})
        return {"investments": investments}

    def get_investments_by_group(self, data, group_by):
        """Group investment data by month or year (mirrors TS getInvestmentsByGroup)."""
        items = []
        for item in data:
            inv_val = item.get("investmentValueWithCurrencyEffect", 0)
            val = inv_val.toNumber() if isinstance(inv_val, Big) else float(inv_val)
            items.append({"date": item.get("date", ""), "investment": val})
        return self._group_by_period(items, group_by)

    @staticmethod
    def _build_holding_dict(pos, extra=None):
        """Build a holding dict from a position, reducing duplication between get_holdings and get_details."""
        sym = pos.get("symbol", "")
        investment = pos.get("investment", Big(0))
        quantity = pos.get("quantity", Big(0))
        fee = pos.get("fee", Big(0))
        np_ = pos.get("netPerformance", Big(0)) or Big(0)

        h = {
            "symbol": sym,
            "quantity": _to_num(quantity),
            "investment": _to_num(investment),
            "currency": pos.get("currency", "USD"),
            "dataSource": pos.get("dataSource", "YAHOO"),
            "dateOfFirstActivity": pos.get("dateOfFirstActivity"),
            "averagePrice": _to_num(pos.get("averagePrice", 0)),
            "marketPrice": pos.get("marketPrice", 0),
            "marketPriceInBaseCurrency": pos.get("marketPriceInBaseCurrency", 0),
            "fee": _to_num(fee),
            "netPerformance": _to_num(np_),
            "grossPerformance": _to_num(pos.get("grossPerformance", 0)),
            "valueInBaseCurrency": _to_num(pos.get("valueInBaseCurrency", 0)),
            "activitiesCount": pos.get("activitiesCount", 0),
            "tags": pos.get("tags", []),
        }
        if extra:
            h.update(extra)
        return sym, h

    def get_holdings(self) -> dict:
        """Return holdings: {holdings: {symbol: {...}}}."""
        snapshot = self._compute_snapshot()
        holdings = {}
        for pos in snapshot.get("positions", []):
            sym, h = self._build_holding_dict(pos, extra={
                "netPerformancePercentage": _to_num(pos.get("netPerformancePercentage", 0)),
            })
            holdings[sym] = h
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
            investment = pos.get("investment", Big(0))
            np_ = pos.get("netPerformance", Big(0)) or Big(0)
            fee = pos.get("fee", Big(0))
            value_base = pos.get("valueInBaseCurrency", Big(0))

            total_investment = total_investment.plus(investment)
            total_net_perf = total_net_perf.plus(np_)
            total_value_base = total_value_base.plus(value_base)
            total_fees = total_fees.plus(fee)

            inv_val = _to_num(investment)
            np_val = _to_num(np_)
            sym, h = self._build_holding_dict(pos, extra={
                "netPerformancePercent": (np_val / inv_val) if inv_val != 0 else 0,
            })
            holdings[sym] = h

        created_at = min((a["date"] for a in self._orders), default=None) if self._orders else None
        tv = _to_num(total_value_base)

        return {
            "accounts": {
                "default": {"balance": 0.0, "currency": base_currency, "name": "Default Account", "valueInBaseCurrency": tv}
            },
            "createdAt": created_at,
            "holdings": holdings,
            "platforms": {
                "default": {"balance": 0.0, "currency": base_currency, "name": "Default Platform", "valueInBaseCurrency": tv}
            },
            "summary": {
                "totalInvestment": _to_num(total_investment),
                "netPerformance": _to_num(total_net_perf),
                "currentValueInBaseCurrency": tv,
                "totalFees": _to_num(total_fees),
            },
            "hasError": snapshot.get("hasErrors", False),
        }

    @staticmethod
    def _group_by_period(items, group_by):
        """Group items by month or year period."""
        grouped = {}
        for item in items:
            d = item["date"]
            key = d[:7] if group_by == "month" else d[:4]
            grouped[key] = grouped.get(key, 0.0) + item["investment"]
        result = []
        for k in sorted(grouped.keys()):
            suffix = "-01" if group_by == "month" else "-01-01"
            result.append({"date": f"{k}{suffix}", "investment": grouped[k]})
        return result

    def get_dividends(self, group_by=None) -> dict:
        """Return dividends: {dividends: [{date, investment}]}."""
        dividend_acts = [a for a in self._orders if a["type"] == "DIVIDEND"]
        if not dividend_acts:
            return {"dividends": []}
        dividends = []
        for act in dividend_acts:
            amount = act["quantity"].mul(act["unitPrice"])
            dividends.append({"date": act["date"], "investment": amount.toNumber()})
        if group_by:
            return {"dividends": self._group_by_period(dividends, group_by)}
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

