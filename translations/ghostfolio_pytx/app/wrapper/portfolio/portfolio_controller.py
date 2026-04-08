"""Mirrors portfolio.controller.ts — FastAPI routes for portfolio endpoints.

Thin routing layer that delegates all computation to the calculator via
PortfolioService. Part of the immutable wrapper layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .portfolio_service import PortfolioService
from .current_rate_service import CurrentRateService
from app.implementation.portfolio.calculator.roai.portfolio_calculator import (
    RoaiPortfolioCalculator,
)

router = APIRouter()


def _service_from_user(user) -> PortfolioService:
    rate_svc = CurrentRateService(user.market_data)
    calculator = RoaiPortfolioCalculator(user.activities, rate_svc)
    return PortfolioService(calculator, user.activities, user.base_currency)


def create_portfolio_router(get_user) -> APIRouter:
    """Build and return the portfolio router with the given auth dependency."""

    @router.get("/api/v2/portfolio/performance")
    def get_performance(range: str = "max", user=Depends(get_user)) -> dict:
        return _service_from_user(user).get_performance()

    @router.get("/api/v1/portfolio/investments")
    def get_investments(
        range: str = "max", groupBy: str | None = None, user=Depends(get_user),
    ) -> dict:
        return _service_from_user(user).get_investments(group_by=groupBy)

    @router.get("/api/v1/portfolio/holdings")
    def get_holdings(range: str = "max", user=Depends(get_user)) -> dict:
        return _service_from_user(user).get_holdings()

    @router.get("/api/v1/portfolio/details")
    def get_details(range: str = "max", user=Depends(get_user)) -> dict:
        return _service_from_user(user).get_details()

    @router.get("/api/v1/portfolio/dividends")
    def get_dividends(
        range: str = "max", groupBy: str | None = None, user=Depends(get_user),
    ) -> dict:
        return _service_from_user(user).get_dividends(group_by=groupBy)

    @router.get("/api/v1/portfolio/report")
    def get_report(user=Depends(get_user)) -> dict:
        return _service_from_user(user).get_report()

    return router
