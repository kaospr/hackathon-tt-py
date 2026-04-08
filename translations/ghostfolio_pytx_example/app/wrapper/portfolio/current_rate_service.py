"""Mirrors current-rate.service.ts — resolves market prices from seeded data."""
from __future__ import annotations

from datetime import date as D


class CurrentRateService:
    """Resolves market prices from seeded data.

    In the original Ghostfolio this service fetches live prices from data
    providers (Yahoo Finance, etc.) and caches them. Here it reads from
    the in-memory market data seeded via the API.
    """

    def __init__(self, market_data: dict[str, dict[str, list[dict]]]) -> None:
        self._market_data = market_data

    def get_price(self, symbol: str, target_date: str) -> float | None:
        for ds_map in self._market_data.values():
            if symbol in ds_map:
                for p in ds_map[symbol]:
                    if p["date"] == target_date:
                        return float(p["marketPrice"])
        return None

    def get_latest_price(self, symbol: str) -> float:
        today = D.today().isoformat()
        price = self.get_price(symbol, today)
        if price is not None:
            return price
        latest_price = None
        latest_date = ""
        for ds_map in self._market_data.values():
            if symbol in ds_map:
                for p in ds_map[symbol]:
                    if p["date"] >= latest_date:
                        latest_date = p["date"]
                        latest_price = float(p["marketPrice"])
        return latest_price if latest_price is not None else 0.0

    def get_nearest_price(self, symbol: str, target_date: str) -> float:
        exact = self.get_price(symbol, target_date)
        if exact is not None:
            return exact
        best_price = 0.0
        best_date = ""
        for ds_map in self._market_data.values():
            if symbol in ds_map:
                for p in ds_map[symbol]:
                    if p["date"] <= target_date and p["date"] > best_date:
                        best_date = p["date"]
                        best_price = float(p["marketPrice"])
        return best_price

    def all_dates_in_range(self, start: str, end: str) -> set[str]:
        dates: set[str] = set()
        for ds_map in self._market_data.values():
            for prices in ds_map.values():
                for p in prices:
                    d = p["date"]
                    if start <= d <= end:
                        dates.add(d)
        return dates
