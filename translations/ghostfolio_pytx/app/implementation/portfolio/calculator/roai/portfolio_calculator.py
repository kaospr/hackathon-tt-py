"""ROAI (Return on Annualized Investment) portfolio calculator.

Processes activities chronologically, tracks average cost basis, and
computes realized / unrealized P&L. Implements all portfolio endpoint
logic: performance, investments, holdings, details, dividends, report.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date as D, timedelta

from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator


_TYPE_ORDER = {"BUY": 0, "SELL": 1, "DIVIDEND": 2, "FEE": 3, "LIABILITY": 4}


class RoaiPortfolioCalculator(PortfolioCalculator):
    """ROAI calculator — full implementation."""

    def __init__(self, activities, current_rate_service):
        super().__init__(activities, current_rate_service)
        self._cached_result: dict | None = None

    # ------------------------------------------------------------------
    # Core computation (position math)
    # ------------------------------------------------------------------

    def _ensure_computed(self) -> dict:
        if self._cached_result is None:
            self._cached_result = self._compute()
        return self._cached_result

    def _compute(self) -> dict:
        sorted_acts = self.sorted_activities()
        symbols: dict[str, dict] = {}
        investment_deltas: list[dict] = []
        total_fees = 0.0
        symbol_fees: dict[str, float] = {}

        for act in sorted_acts:
            sym = act.get("symbol", "")
            act_type = act.get("type", "BUY")
            qty = float(act.get("quantity") or 0)
            price = float(act.get("unitPrice") or 0)
            fee = float(act.get("fee") or 0)
            act_date = act.get("date", "")

            total_fees += fee
            if sym:
                symbol_fees[sym] = symbol_fees.get(sym, 0.0) + fee

            if act_type in ("DIVIDEND", "FEE", "LIABILITY"):
                continue

            if sym not in symbols:
                symbols[sym] = {
                    "quantity": 0.0,
                    "investment": 0.0,
                    "avg_price": 0.0,
                    "total_buy_cost": 0.0,
                    "realized_pnl": 0.0,
                }

            s = symbols[sym]
            if act_type == "BUY":
                self._process_buy(s, qty, price, act_date, investment_deltas, sym)
            elif act_type == "SELL":
                self._process_sell(s, qty, price, act_date, investment_deltas, sym)

        return {
            "symbols": symbols,
            "investment_deltas": investment_deltas,
            "total_fees": total_fees,
            "sorted_activities": sorted_acts,
            "symbol_fees": symbol_fees,
        }

    # ------------------------------------------------------------------
    # GET /api/v2/portfolio/performance
    # ------------------------------------------------------------------

    def get_performance(self) -> dict:
        portfolio = self._ensure_computed()
        symbols = portfolio["symbols"]
        total_fees = portfolio["total_fees"]

        total_investment = 0.0
        total_current_value = 0.0
        total_realized_pnl = 0.0
        total_twi = 0.0
        open_investment = 0.0

        for sym, s in symbols.items():
            qty = s["quantity"]
            inv = s["investment"]
            total_investment += inv

            if abs(qty) > 1e-12:
                current_price = self.current_rate_service.get_latest_price(sym)
                total_current_value += abs(qty) * current_price
                open_investment += inv

            total_realized_pnl += s["realized_pnl"]
            total_twi += s["total_buy_cost"]

        unrealized_pnl = total_current_value - open_investment
        net_performance = total_realized_pnl + unrealized_pnl - total_fees

        if abs(total_investment) > 1e-10:
            denom = total_investment
        elif total_twi > 1e-10:
            denom = total_twi
        else:
            denom = 1.0
        net_perf_pct = net_performance / denom if abs(denom) > 1e-10 else 0.0

        chart = self._build_chart(portfolio)
        first_date = min(a["date"] for a in self.activities)

        return {
            "chart": chart,
            "firstOrderDate": first_date,
            "performance": {
                "currentNetWorth": total_current_value,
                "currentValue": total_current_value,
                "currentValueInBaseCurrency": total_current_value,
                "netPerformance": net_performance,
                "netPerformancePercentage": net_perf_pct,
                "netPerformancePercentageWithCurrencyEffect": net_perf_pct,
                "netPerformanceWithCurrencyEffect": net_performance,
                "totalFees": total_fees,
                "totalInvestment": total_investment,
                "totalLiabilities": 0.0,
                "totalValueables": 0.0,
            },
        }

    # ------------------------------------------------------------------
    # GET /api/v1/portfolio/investments
    # ------------------------------------------------------------------

    def get_investments(self, group_by: str | None = None) -> dict:
        deltas = self._ensure_computed()["investment_deltas"]
        if group_by is None:
            return self._investments_daily(deltas)
        elif group_by == "month":
            return self._investments_by_month(deltas)
        elif group_by == "year":
            return self._investments_by_year(deltas)
        return {"investments": []}

    # ------------------------------------------------------------------
    # GET /api/v1/portfolio/holdings
    # ------------------------------------------------------------------

    def get_holdings(self) -> dict:
        symbols = self._ensure_computed()["symbols"]
        holdings: dict[str, dict] = {}
        for sym, s in symbols.items():
            if abs(s["quantity"]) < 1e-12:
                continue
            current_price = self.current_rate_service.get_latest_price(sym)
            holdings[sym] = {
                "symbol": sym,
                "quantity": s["quantity"],
                "investment": s["investment"],
                "marketPrice": current_price,
                "averagePrice": s["avg_price"],
            }
        return {"holdings": holdings}

    # ------------------------------------------------------------------
    # GET /api/v1/portfolio/details
    # ------------------------------------------------------------------

    def get_details(self, base_currency: str = "USD") -> dict:
        result = self._ensure_computed()
        symbols = result["symbols"]
        sym_fees = result["symbol_fees"]
        total_fees = result["total_fees"]

        holdings: dict[str, dict] = {}
        total_current_value = 0.0
        total_investment = 0.0
        total_realized_pnl = 0.0

        for sym, s in symbols.items():
            qty = s["quantity"]
            inv = s["investment"]
            total_investment += inv
            total_realized_pnl += s["realized_pnl"]
            current_price = self.current_rate_service.get_latest_price(sym)
            current_value = abs(qty) * current_price if abs(qty) > 1e-12 else 0.0
            if abs(qty) > 1e-12:
                total_current_value += current_value
            fees = sym_fees.get(sym, 0.0)

            net_perf = (current_value - inv) + s["realized_pnl"] - fees
            if abs(inv) > 1e-10:
                net_perf_pct = net_perf / inv
            elif s["total_buy_cost"] > 1e-10:
                net_perf_pct = net_perf / s["total_buy_cost"]
            else:
                net_perf_pct = 0.0

            gross_perf = (current_value - inv) + s["realized_pnl"]
            if abs(inv) > 1e-10:
                gross_perf_pct = gross_perf / inv
            elif s["total_buy_cost"] > 1e-10:
                gross_perf_pct = gross_perf / s["total_buy_cost"]
            else:
                gross_perf_pct = 0.0

            holdings[sym] = {
                "symbol": sym,
                "quantity": qty,
                "investment": inv,
                "marketPrice": current_price,
                "averagePrice": s["avg_price"],
                "netPerformance": net_perf,
                "netPerformancePercent": net_perf_pct,
                "netPerformancePercentWithCurrencyEffect": net_perf_pct,
                "grossPerformance": gross_perf,
                "grossPerformancePercent": gross_perf_pct,
                "grossPerformancePercentWithCurrencyEffect": gross_perf_pct,
                "grossPerformanceWithCurrencyEffect": gross_perf,
                "netPerformanceWithCurrencyEffect": net_perf,
                "valueInBaseCurrency": current_value,
                "allocationInPercentage": 0.0,
                "activitiesCount": self._count_activities(sym),
                "dividend": self._total_dividends(sym),
                "dateOfFirstActivity": self._first_activity_date(sym),
            }

        open_inv = sum(s["investment"] for s in symbols.values() if abs(s["quantity"]) > 1e-12)
        unrealized = total_current_value - open_inv
        net_performance = total_realized_pnl + unrealized - total_fees

        return {
            "accounts": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Account",
                    "valueInBaseCurrency": total_current_value,
                }
            },
            "createdAt": min(a["date"] for a in self.activities),
            "holdings": holdings,
            "platforms": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Platform",
                    "valueInBaseCurrency": total_current_value,
                }
            },
            "summary": {
                "totalInvestment": total_investment,
                "netPerformance": net_performance,
                "currentValueInBaseCurrency": total_current_value,
                "totalFees": total_fees,
            },
            "hasError": False,
        }

    # ------------------------------------------------------------------
    # GET /api/v1/portfolio/dividends
    # ------------------------------------------------------------------

    def get_dividends(self, group_by: str | None = None) -> dict:
        dividend_acts = [a for a in self.activities if a.get("type") == "DIVIDEND"]
        if not dividend_acts:
            return {"dividends": []}

        items = [
            {"date": a["date"], "investment": float(a.get("quantity") or 0) * float(a.get("unitPrice") or 0)}
            for a in dividend_acts
        ]

        if group_by is None:
            dividends = self._group_dividends_daily(items)
        elif group_by == "month":
            dividends = self._group_dividends_by_month(items)
        elif group_by == "year":
            dividends = self._group_dividends_by_year(items)
        else:
            dividends = items
        return {"dividends": dividends}

    # ------------------------------------------------------------------
    # GET /api/v1/portfolio/report
    # ------------------------------------------------------------------

    def evaluate_report(self) -> dict:
        result = self._ensure_computed()
        symbols = result["symbols"]
        total_fees = result["total_fees"]

        has_holdings = any(abs(s["quantity"]) > 1e-12 for s in symbols.values())
        total_investment = sum(s["investment"] for s in symbols.values())
        currencies = set(
            a.get("currency", "")
            for a in self.activities
            if a.get("type") in ("BUY", "SELL") and a.get("currency")
        )
        fee_ratio = total_fees / total_investment if abs(total_investment) > 1e-10 else 0.0

        categories = [
            {
                "key": "accounts",
                "name": "Accounts",
                "rules": [
                    {"key": "accountClusterRisk", "name": "Account Cluster Risk",
                     "isActive": has_holdings, "value": False},
                ],
            },
            {
                "key": "currencies",
                "name": "Currencies",
                "rules": [
                    {"key": "currencyClusterRisk", "name": "Currency Cluster Risk",
                     "isActive": has_holdings, "value": len(currencies) > 1},
                ],
            },
            {
                "key": "fees",
                "name": "Fees",
                "rules": [
                    {"key": "feeRatio", "name": "Fee Ratio",
                     "isActive": has_holdings and total_fees > 0, "value": fee_ratio < 0.015},
                ],
            },
        ]

        active = sum(1 for cat in categories for r in cat["rules"] if r["isActive"])
        fulfilled = sum(1 for cat in categories for r in cat["rules"] if r["isActive"] and r.get("value"))

        return {
            "xRay": {
                "categories": categories,
                "statistics": {"rulesActiveCount": active, "rulesFulfilledCount": fulfilled},
            }
        }

    # ------------------------------------------------------------------
    # Chart building
    # ------------------------------------------------------------------

    def _build_chart(self, portfolio: dict) -> list[dict]:
        activity_dates = [a["date"] for a in self.activities]
        first_date = min(activity_dates)
        start = D.fromisoformat(first_date) - timedelta(days=1)
        end = D.today()

        chart_dates: set[str] = {start.isoformat()}
        for a in self.activities:
            d = D.fromisoformat(a["date"])
            if start <= d <= end:
                chart_dates.add(a["date"])

        chart_dates.update(
            self.current_rate_service.all_dates_in_range(start.isoformat(), end.isoformat())
        )

        for year in range(start.year, end.year + 1):
            for boundary in (D(year, 1, 1), D(year, 12, 31)):
                if start < boundary <= end:
                    chart_dates.add(boundary.isoformat())
        chart_dates.add(end.isoformat())

        sorted_dates = sorted(chart_dates)

        inv_delta_by_date: dict[str, float] = defaultdict(float)
        for d in portfolio["investment_deltas"]:
            inv_delta_by_date[d["date"]] += d["investment"]

        sorted_acts = sorted(
            self.activities,
            key=lambda a: (a["date"], _TYPE_ORDER.get(a.get("type", ""), 5)),
        )

        chart = []
        sym_state: dict[str, dict] = {}
        cumulative_fees = 0.0
        act_idx = 0

        for chart_date in sorted_dates:
            while act_idx < len(sorted_acts) and sorted_acts[act_idx]["date"] <= chart_date:
                act = sorted_acts[act_idx]
                act_type = act.get("type", "BUY")
                sym = act.get("symbol", "")
                qty = float(act.get("quantity") or 0)
                price = float(act.get("unitPrice") or 0)
                fee = float(act.get("fee") or 0)

                cumulative_fees += fee
                if act_type in ("DIVIDEND", "FEE", "LIABILITY"):
                    act_idx += 1
                    continue

                if sym not in sym_state:
                    sym_state[sym] = {"quantity": 0.0, "investment": 0.0, "avg_price": 0.0}

                ss = sym_state[sym]
                if act_type == "BUY":
                    self._chart_buy(ss, qty, price)
                elif act_type == "SELL":
                    self._chart_sell(ss, qty, price)

                act_idx += 1

            total_value = 0.0
            cumulative_investment = 0.0
            for sym, ss in sym_state.items():
                cumulative_investment += ss["investment"]
                if abs(ss["quantity"]) > 1e-12:
                    mp = self.current_rate_service.get_nearest_price(sym, chart_date)
                    total_value += abs(ss["quantity"]) * mp

            net_perf = total_value - cumulative_investment - cumulative_fees
            net_perf_pct = (
                net_perf / cumulative_investment
                if abs(cumulative_investment) > 1e-10
                else 0.0
            )

            chart.append({
                "date": chart_date,
                "netWorth": total_value,
                "value": total_value,
                "totalInvestment": cumulative_investment,
                "netPerformance": net_perf,
                "netPerformanceInPercentage": net_perf_pct,
                "netPerformanceInPercentageWithCurrencyEffect": net_perf_pct,
                "investmentValueWithCurrencyEffect": inv_delta_by_date.get(chart_date, 0.0),
            })

        return chart

    @staticmethod
    def _chart_buy(ss: dict, qty: float, price: float) -> None:
        if ss["quantity"] < -1e-12:
            cover_qty = min(qty, abs(ss["quantity"]))
            ss["investment"] += cover_qty * price
            ss["quantity"] += cover_qty
            remaining = qty - cover_qty
            if remaining > 1e-12:
                new_cost = remaining * price
                new_qty = ss["quantity"] + remaining
                if new_qty > 1e-12:
                    ss["avg_price"] = (ss["quantity"] * ss["avg_price"] + new_cost) / new_qty
                ss["investment"] += new_cost
                ss["quantity"] = new_qty
        else:
            cost = qty * price
            new_qty = ss["quantity"] + qty
            if new_qty > 1e-12:
                ss["avg_price"] = (ss["quantity"] * ss["avg_price"] + cost) / new_qty
            ss["investment"] += cost
            ss["quantity"] = new_qty

    @staticmethod
    def _chart_sell(ss: dict, qty: float, price: float) -> None:
        if ss["quantity"] > 1e-12:
            sell_qty = min(qty, ss["quantity"])
            ss["investment"] -= sell_qty * ss["avg_price"]
            ss["quantity"] -= sell_qty
            remaining = qty - sell_qty
            if remaining > 1e-12:
                ss["quantity"] -= remaining
                ss["avg_price"] = price
        else:
            ss["quantity"] -= qty
            if abs(ss["quantity"] + qty) < 1e-12:
                ss["avg_price"] = price
            else:
                prev_qty = abs(ss["quantity"] + qty)
                ss["avg_price"] = (prev_qty * abs(ss["avg_price"]) + qty * price) / (prev_qty + qty)

    # ------------------------------------------------------------------
    # Transaction processing
    # ------------------------------------------------------------------

    @staticmethod
    def _process_buy(s, qty, price, act_date, deltas, sym):
        if s["quantity"] < -1e-12:
            cover_qty = min(qty, abs(s["quantity"]))
            cost = cover_qty * price
            s["realized_pnl"] += cover_qty * (abs(s["avg_price"]) - price)
            s["investment"] += cost
            s["total_buy_cost"] += cost
            deltas.append({"date": act_date, "investment": cost, "symbol": sym})
            remaining = qty - cover_qty
            s["quantity"] += cover_qty
            if remaining > 1e-12:
                new_cost = remaining * price
                new_qty = s["quantity"] + remaining
                if new_qty > 1e-12:
                    s["avg_price"] = (s["quantity"] * s["avg_price"] + new_cost) / new_qty
                s["investment"] += new_cost
                s["total_buy_cost"] += new_cost
                s["quantity"] = new_qty
                deltas.append({"date": act_date, "investment": new_cost, "symbol": sym})
        else:
            cost = qty * price
            new_qty = s["quantity"] + qty
            if new_qty > 1e-12:
                s["avg_price"] = (s["quantity"] * s["avg_price"] + cost) / new_qty
            s["investment"] += cost
            s["total_buy_cost"] += cost
            s["quantity"] = new_qty
            deltas.append({"date": act_date, "investment": cost, "symbol": sym})

    @staticmethod
    def _process_sell(s, qty, price, act_date, deltas, sym):
        if s["quantity"] > 1e-12:
            sell_qty = min(qty, s["quantity"])
            cost_returned = sell_qty * s["avg_price"]
            s["realized_pnl"] += sell_qty * (price - s["avg_price"])
            s["investment"] -= cost_returned
            deltas.append({"date": act_date, "investment": -cost_returned, "symbol": sym})
            s["quantity"] -= sell_qty
            remaining = qty - sell_qty
            if remaining > 1e-12:
                s["quantity"] -= remaining
                s["avg_price"] = price
        else:
            s["quantity"] -= qty
            if abs(s["quantity"] + qty) < 1e-12:
                s["avg_price"] = price
            else:
                prev_qty = abs(s["quantity"] + qty)
                s["avg_price"] = (prev_qty * abs(s["avg_price"]) + qty * price) / (prev_qty + qty)
            deltas.append({"date": act_date, "investment": -qty * price, "symbol": sym})

    # ------------------------------------------------------------------
    # Investment grouping
    # ------------------------------------------------------------------

    @staticmethod
    def _investments_daily(deltas):
        by_date: dict[str, float] = {}
        for d in deltas:
            by_date[d["date"]] = by_date.get(d["date"], 0.0) + d["investment"]
        return {
            "investments": [
                {"date": dt, "investment": inv}
                for dt, inv in sorted(by_date.items())
                if abs(inv) > 1e-10
            ]
        }

    def _investments_by_month(self, deltas):
        by_month: dict[str, float] = {}
        for d in deltas:
            dt = D.fromisoformat(d["date"])
            key = D(dt.year, dt.month, 1).isoformat()
            by_month[key] = by_month.get(key, 0.0) + d["investment"]

        first = min(D.fromisoformat(a["date"]) for a in self.activities)
        end_date = D.today()
        months: list[str] = []
        cur = D(first.year, first.month, 1)
        while cur <= end_date:
            months.append(cur.isoformat())
            cur = D(cur.year + 1, 1, 1) if cur.month == 12 else D(cur.year, cur.month + 1, 1)

        return {"investments": [{"date": m, "investment": by_month.get(m, 0.0)} for m in months]}

    def _investments_by_year(self, deltas):
        by_year: dict[str, float] = {}
        for d in deltas:
            dt = D.fromisoformat(d["date"])
            key = D(dt.year, 1, 1).isoformat()
            by_year[key] = by_year.get(key, 0.0) + d["investment"]

        first_year = min(D.fromisoformat(a["date"]) for a in self.activities).year
        last_year = D.today().year

        return {
            "investments": [
                {"date": D(y, 1, 1).isoformat(), "investment": by_year.get(D(y, 1, 1).isoformat(), 0.0)}
                for y in range(first_year, last_year + 1)
            ]
        }

    # ------------------------------------------------------------------
    # Dividend grouping
    # ------------------------------------------------------------------

    @staticmethod
    def _group_dividends_daily(items):
        by_date: dict[str, float] = {}
        for item in items:
            by_date[item["date"]] = by_date.get(item["date"], 0.0) + item["investment"]
        return [{"date": dt, "investment": inv} for dt, inv in sorted(by_date.items())]

    @staticmethod
    def _group_dividends_by_month(items):
        by_month: dict[str, float] = {}
        for item in items:
            dt = D.fromisoformat(item["date"])
            key = D(dt.year, dt.month, 1).isoformat()
            by_month[key] = by_month.get(key, 0.0) + item["investment"]
        return [{"date": dt, "investment": inv} for dt, inv in sorted(by_month.items())]

    @staticmethod
    def _group_dividends_by_year(items):
        by_year: dict[str, float] = {}
        for item in items:
            dt = D.fromisoformat(item["date"])
            key = D(dt.year, 1, 1).isoformat()
            by_year[key] = by_year.get(key, 0.0) + item["investment"]
        return [{"date": dt, "investment": inv} for dt, inv in sorted(by_year.items())]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_activities(self, symbol: str) -> int:
        return sum(1 for a in self.activities if a.get("symbol") == symbol)

    def _total_dividends(self, symbol: str) -> float:
        return sum(
            float(a.get("quantity") or 0) * float(a.get("unitPrice") or 0)
            for a in self.activities
            if a.get("symbol") == symbol and a.get("type") == "DIVIDEND"
        )

    def _first_activity_date(self, symbol: str) -> str | None:
        dates = [a["date"] for a in self.activities if a.get("symbol") == symbol]
        return min(dates) if dates else None
