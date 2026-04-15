"""Big number class compatible with Big.js API, wrapping Python Decimal."""
from __future__ import annotations

from decimal import Decimal


class Big:
    """Arbitrary-precision number compatible with Big.js method API."""

    def __init__(self, value=0):
        if isinstance(value, Big):
            self._val = value._val
        elif isinstance(value, Decimal):
            self._val = value
        elif value is None:
            self._val = Decimal(0)
        else:
            self._val = Decimal(str(value))

    def plus(self, other) -> Big:
        return Big(self._val + Big(other)._val)

    def minus(self, other) -> Big:
        return Big(self._val - Big(other)._val)

    def mul(self, other) -> Big:
        return Big(self._val * Big(other)._val)

    def div(self, other) -> Big:
        return Big(self._val / Big(other)._val)

    def add(self, other) -> Big:
        return self.plus(other)

    def eq(self, other) -> bool:
        return self._val == Big(other)._val

    def gt(self, other) -> bool:
        return self._val > Big(other)._val

    def gte(self, other) -> bool:
        return self._val >= Big(other)._val

    def lt(self, other) -> bool:
        return self._val < Big(other)._val

    def lte(self, other) -> bool:
        return self._val <= Big(other)._val

    def abs(self) -> Big:
        return Big(abs(self._val))

    def toNumber(self) -> float:
        return float(self._val)

    def toFixed(self, n: int = 0) -> str:
        return f"{self._val:.{n}f}"

    # Python operator support
    def __add__(self, other): return self.plus(other)
    def __radd__(self, other): return Big(other).plus(self)
    def __sub__(self, other): return self.minus(other)
    def __rsub__(self, other): return Big(other).minus(self)
    def __mul__(self, other): return self.mul(other)
    def __rmul__(self, other): return Big(other).mul(self)
    def __truediv__(self, other): return self.div(other)
    def __neg__(self): return Big(-self._val)
    def __eq__(self, other): return self.eq(other) if isinstance(other, Big) else self._val == Decimal(str(other)) if other is not None else False
    def __gt__(self, other): return self.gt(other)
    def __lt__(self, other): return self.lt(other)
    def __ge__(self, other): return self.gte(other)
    def __le__(self, other): return self.lte(other)
    def __float__(self): return float(self._val)
    def __bool__(self): return self._val != 0
    def __repr__(self): return f"Big({self._val})"
    def __hash__(self): return hash(self._val)
