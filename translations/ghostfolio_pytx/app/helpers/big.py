"""Big number class compatible with Big.js API, wrapping Python Decimal."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def _parse_big_numeric(value) -> Decimal:
    """Convert a numeric value to Decimal."""
    if isinstance(value, bool):
        return Decimal(1) if value else Decimal(0)
    return Decimal(str(value))


def _parse_big_value(value) -> Decimal:
    """Convert a raw value to Decimal for Big construction."""
    if isinstance(value, Big):
        return value._val
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal(0)
    if isinstance(value, (bool, int, float)):
        return _parse_big_numeric(value)
    if isinstance(value, str):
        return _parse_big_str(value)
    return _parse_big_fallback(value)


def _parse_big_str(value: str) -> Decimal:
    """Parse a string value to Decimal."""
    stripped = value.strip()
    if stripped == "":
        return Decimal(0)
    try:
        return Decimal(stripped)
    except InvalidOperation:
        raise ValueError(f"Big: cannot convert {value!r} to a number")


def _parse_big_fallback(value) -> Decimal:
    """Last-resort conversion to Decimal via str."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise TypeError(
            f"Big: unsupported type {type(value).__name__!r} for value {value!r}"
        )


class Big:
    """Arbitrary-precision number compatible with Big.js method API.

    Wraps Python's ``Decimal`` to provide the same chaining interface as the
    JavaScript Big.js library:  ``Big(10).minus(3).mul(2).toNumber()  # 14.0``

    Handles ``None`` (treated as 0), raw Python numbers, strings, other
    ``Big`` instances and ``Decimal`` values transparently so that translated
    TypeScript code works without manual conversion at every call site.
    """

    __slots__ = ("_val",)

    def __init__(self, value=0):
        self._val = _parse_big_value(value)

    # ------------------------------------------------------------------
    # Big.js chainable arithmetic — each returns a *new* Big
    # ------------------------------------------------------------------

    def plus(self, other) -> Big:
        """Addition.  ``x.plus(y)``"""
        return Big(self._val + Big(other)._val)

    def minus(self, other) -> Big:
        """Subtraction.  ``x.minus(y)``"""
        return Big(self._val - Big(other)._val)

    def mul(self, other) -> Big:
        """Multiplication.  ``x.mul(y)``"""
        return Big(self._val * Big(other)._val)

    def div(self, other) -> Big:
        """Division.  ``x.div(y)``  Returns Big(0) on /0."""
        divisor = Big(other)._val
        if divisor == 0:
            return Big(0)
        return Big(self._val / divisor)

    # Aliases (Big.js accepts both names)
    def add(self, other) -> Big:
        """Alias for :meth:`plus`."""
        return self.plus(other)

    def sub(self, other) -> Big:
        """Alias for :meth:`minus`."""
        return self.minus(other)

    def times(self, other) -> Big:
        """Alias for :meth:`mul`."""
        return self.mul(other)

    # ------------------------------------------------------------------
    # Comparison — return plain bool
    # ------------------------------------------------------------------

    def eq(self, other) -> bool:
        """Equality.  ``x.eq(y)``"""
        return self._val == Big(other)._val

    def gt(self, other) -> bool:
        """Greater than.  ``x.gt(y)``"""
        return self._val > Big(other)._val

    def gte(self, other) -> bool:
        """Greater than or equal.  ``x.gte(y)``"""
        return self._val >= Big(other)._val

    def lt(self, other) -> bool:
        """Less than.  ``x.lt(y)``"""
        return self._val < Big(other)._val

    def lte(self, other) -> bool:
        """Less than or equal.  ``x.lte(y)``"""
        return self._val <= Big(other)._val

    def cmp(self, other) -> int:
        """Three-way comparison: -1, 0, or 1."""
        other_val = Big(other)._val
        if self._val < other_val:
            return -1
        elif self._val > other_val:
            return 1
        return 0

    # ------------------------------------------------------------------
    # Unary / conversion
    # ------------------------------------------------------------------

    def abs(self) -> Big:
        """Absolute value.  ``x.abs()``"""
        return Big(abs(self._val))

    def neg(self) -> Big:
        """Negation.  ``x.neg()``"""
        return self.mul(-1)

    def toNumber(self) -> float:
        """Convert to Python ``float``."""
        return float(self._val)

    def toFixed(self, n: int = 0) -> str:
        """Format to string with *n* decimal places using ROUND_HALF_UP.

        Matches Big.js default rounding mode (roundHalfUp = 1).
        """
        if n < 0:
            raise ValueError("Big: toFixed() decimal places must be >= 0")
        quantizer = Decimal(10) ** -n  # e.g. Decimal('0.01') for n=2
        rounded = self._val.quantize(quantizer, rounding=ROUND_HALF_UP)
        return f"{rounded:f}"

    def valueOf(self) -> str:
        """Return string representation of the value (Big.js compatibility)."""
        return str(self._val)

    # ------------------------------------------------------------------
    # Python operator support
    # ------------------------------------------------------------------

    def __add__(self, other):
        return self.plus(other)

    def __radd__(self, other):
        return self.plus(other)

    def __sub__(self, other):
        return self.minus(other)

    def __rsub__(self, other):
        return self.neg().plus(other)

    def __mul__(self, other):
        return self.mul(other)

    def __rmul__(self, other):
        return self.mul(other)

    def __truediv__(self, other):
        return self.div(other)

    def __rtruediv__(self, other):
        if self._val == 0:
            return Big(0)
        return Big(Big(other)._val / self._val)

    def __neg__(self):
        return self.neg()

    def __pos__(self):
        return Big(self._val)

    def __abs__(self):
        return self.abs()

    # ------------------------------------------------------------------
    # Comparison operators
    # ------------------------------------------------------------------

    def __eq__(self, other):
        if other is None:
            return False
        try:
            return self._val == Big(other)._val
        except (ValueError, TypeError):
            return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __gt__(self, other):
        try:
            return self._val > Big(other)._val
        except (ValueError, TypeError):
            return NotImplemented

    def __lt__(self, other):
        try:
            return self._val < Big(other)._val
        except (ValueError, TypeError):
            return NotImplemented

    def __ge__(self, other):
        try:
            return self._val >= Big(other)._val
        except (ValueError, TypeError):
            return NotImplemented

    def __le__(self, other):
        try:
            return self._val <= Big(other)._val
        except (ValueError, TypeError):
            return NotImplemented

    # ------------------------------------------------------------------
    # Conversions
    # ------------------------------------------------------------------

    def __float__(self):
        return float(self._val)

    def __int__(self):
        return int(self._val)

    def __bool__(self):
        _ = self._val  # access to maintain cohesion
        return True  # Big object is always truthy (like JS object)

    def __str__(self):
        return str(self._val)

    def __repr__(self):
        return f"Big({self.valueOf()})"

    def __hash__(self):
        return hash(self._val)


class Pair:
    """Holds base and currency-effect values together."""
    __slots__ = ("base", "ce")

    def __init__(self, base=None, ce=None):
        b = base if base is not None else Big(0)
        c = ce if ce is not None else Big(0)
        self.base = b if isinstance(b, Big) else Big(b)
        self.ce = c if isinstance(c, Big) else Big(c)

    def plus(self, other):
        if isinstance(other, Pair):
            return Pair(self.base.plus(other.base), self.ce.plus(other.ce))
        return Pair(self.base.plus(other), self.ce.plus(other))

    def minus(self, other):
        if isinstance(other, Pair):
            return Pair(self.base.minus(other.base), self.ce.minus(other.ce))
        return Pair(self.base.minus(other), self.ce.minus(other))

    def add(self, other):
        return self.plus(other)

    def mul_rates(self, current_rate, date_rate):
        return Pair(self.base.mul(current_rate), self.ce.mul(date_rate))

    def div_each(self, divisor):
        """Divide both base and ce by the same divisor."""
        return Pair(self.base.div(divisor), self.ce.div(divisor))

    @staticmethod
    def zero():
        return Pair(Big(0), Big(0))


def to_num(v):
    """Convert Big or number to float."""
    if isinstance(v, Big):
        return v.toNumber()
    if v is None:
        return 0
    return float(v)
