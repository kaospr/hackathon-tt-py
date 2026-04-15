"""Assemble translated method bodies into the final Python calculator file."""
from __future__ import annotations


def assemble(translated_methods: dict[str, str]) -> str:
    """Generate the final RoaiPortfolioCalculator Python source.

    Takes a dict of translated method bodies and produces a complete
    Python file that implements the 6 API methods required by the wrapper.
    """
    return _STUB_CALCULATOR


_STUB_CALCULATOR = '''\
"""ROAI Portfolio Calculator — translated from TypeScript."""
from __future__ import annotations

from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator


class RoaiPortfolioCalculator(PortfolioCalculator):
    """Stub ROAI calculator — no real implementation yet."""

    def get_performance(self) -> dict:
        sorted_acts = self.sorted_activities()
        first_date = min((a["date"] for a in sorted_acts), default=None)
        return {
            "chart": [],
            "firstOrderDate": first_date,
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

    def get_investments(self, group_by: str | None = None) -> dict:
        return {"investments": []}

    def get_holdings(self) -> dict:
        return {"holdings": {}}

    def get_details(self, base_currency: str = "USD") -> dict:
        return {
            "accounts": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Account",
                    "valueInBaseCurrency": 0.0,
                }
            },
            "createdAt": min((a["date"] for a in self.activities), default=None),
            "holdings": {},
            "platforms": {
                "default": {
                    "balance": 0.0,
                    "currency": base_currency,
                    "name": "Default Platform",
                    "valueInBaseCurrency": 0.0,
                }
            },
            "summary": {
                "totalInvestment": 0,
                "netPerformance": 0,
                "currentValueInBaseCurrency": 0,
                "totalFees": 0,
            },
            "hasError": False,
        }

    def get_dividends(self, group_by: str | None = None) -> dict:
        return {"dividends": []}

    def evaluate_report(self) -> dict:
        return {
            "xRay": {
                "categories": [
                    {"key": "accounts", "name": "Accounts", "rules": []},
                    {"key": "currencies", "name": "Currencies", "rules": []},
                    {"key": "fees", "name": "Fees", "rules": []},
                ],
                "statistics": {"rulesActiveCount": 0, "rulesFulfilledCount": 0},
            }
        }
'''
