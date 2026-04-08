from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SymbolProfile:
    symbol: str
    data_source: str = "YAHOO"


@dataclass
class PortfolioOrder:
    date: str
    fee: float
    quantity: float
    symbol_profile: SymbolProfile
    type: str  # BUY | SELL | DIVIDEND | FEE | LIABILITY
    unit_price: float
