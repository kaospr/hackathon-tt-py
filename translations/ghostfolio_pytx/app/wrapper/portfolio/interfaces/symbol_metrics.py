from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SymbolMetrics:
    quantity: float = 0.0
    investment: float = 0.0
    avg_price: float = 0.0
    total_buy_cost: float = 0.0
    realized_pnl: float = 0.0
