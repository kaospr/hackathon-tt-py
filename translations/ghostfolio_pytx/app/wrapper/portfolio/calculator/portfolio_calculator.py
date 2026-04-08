"""Mirrors calculator/portfolio-calculator.ts — abstract base class.

Defines the calculator interface that implementation classes must fulfill.
Part of the immutable wrapper layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..current_rate_service import CurrentRateService


_TYPE_ORDER = {"BUY": 0, "SELL": 1, "DIVIDEND": 2, "FEE": 3, "LIABILITY": 4}


class PortfolioCalculator(ABC):
    """Base class for portfolio calculators."""

    def __init__(
        self,
        activities: list[dict],
        current_rate_service: CurrentRateService,
    ) -> None:
        self.activities = activities
        self.current_rate_service = current_rate_service

    def sorted_activities(self) -> list[dict]:
        return sorted(
            self.activities,
            key=lambda a: (a["date"], _TYPE_ORDER.get(a.get("type", ""), 5)),
        )

    @abstractmethod
    def get_performance(self) -> dict:
        """Return full performance response: {chart, firstOrderDate, performance}."""

    @abstractmethod
    def get_investments(self, group_by: str | None = None) -> dict:
        """Return investments response: {investments: [{date, investment}]}."""

    @abstractmethod
    def get_holdings(self) -> dict:
        """Return holdings response: {holdings: {symbol: {...}}}."""

    @abstractmethod
    def get_details(self, base_currency: str = "USD") -> dict:
        """Return details response: {accounts, holdings, summary, ...}."""

    @abstractmethod
    def get_dividends(self, group_by: str | None = None) -> dict:
        """Return dividends response: {dividends: [{date, investment}]}."""

    @abstractmethod
    def evaluate_report(self) -> dict:
        """Return report response: {xRay: {categories, statistics}}."""
