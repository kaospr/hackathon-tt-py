"""Mirrors portfolio.service.ts — thin orchestration layer.

Delegates all computation to the injected PortfolioCalculator. Contains
no financial logic — only empty-portfolio guards and response formatting.
Part of the immutable wrapper layer.
"""
from __future__ import annotations


_EMPTY_PERFORMANCE: dict = {
    "chart": [],
    "firstOrderDate": None,
    "performance": {
        "currentNetWorth": 0,
        "currentValue": 0,
        "currentValueInBaseCurrency": 0,
        "netPerformance": 0,
        "netPerformancePercentage": 0,
        "netPerformancePercentageWithCurrencyEffect": 0,
        "netPerformanceWithCurrencyEffect": 0,
        "totalFees": 0,
        "totalInvestment": 0,
        "totalLiabilities": 0.0,
        "totalValueables": 0.0,
    },
}

_EMPTY_DETAILS: dict = {
    "accounts": {},
    "createdAt": None,
    "holdings": {},
    "platforms": {},
    "summary": {
        "totalInvestment": 0,
        "netPerformance": 0,
        "currentValueInBaseCurrency": 0,
    },
    "hasError": False,
}


class PortfolioService:
    """Thin orchestration service — delegates to the calculator."""

    def __init__(self, calculator, activities: list[dict], base_currency: str = "USD") -> None:
        self._calculator = calculator
        self._activities = activities
        self._base_currency = base_currency

    def get_performance(self) -> dict:
        if not self._activities:
            return _EMPTY_PERFORMANCE
        return self._calculator.get_performance()

    def get_investments(self, group_by: str | None = None) -> dict:
        if not self._activities:
            return {"investments": []}
        return self._calculator.get_investments(group_by)

    def get_holdings(self) -> dict:
        if not self._activities:
            return {"holdings": {}}
        return self._calculator.get_holdings()

    def get_details(self) -> dict:
        if not self._activities:
            return _EMPTY_DETAILS
        return self._calculator.get_details(self._base_currency)

    def get_dividends(self, group_by: str | None = None) -> dict:
        if not self._activities:
            return {"dividends": []}
        return self._calculator.get_dividends(group_by)

    def get_report(self) -> dict:
        if not self._activities:
            return {
                "xRay": {
                    "categories": [],
                    "statistics": {"rulesActiveCount": 0, "rulesFulfilledCount": 0},
                }
            }
        return self._calculator.evaluate_report()
