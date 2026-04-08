from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TransactionPointSymbol:
    date: str
    symbol: str
    quantity: float
    investment: float
    avg_price: float
    total_buy_cost: float
    realized_pnl: float
