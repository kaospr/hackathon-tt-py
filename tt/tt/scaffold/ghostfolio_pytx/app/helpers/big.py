"""Big number class compatible with Big.js API, wrapping Python Decimal."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


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
        if isinstance(value, Big):
            self._val = value._val
        elif isinstance(value, Decimal):
            self._val = value
        elif value is None:
            self._val = Decimal(0)
        elif isinstance(value, bool):
            # bool is a subclass of int; handle before int check
            self._val = Decimal(1) if value else Decimal(0)
        elif isinstance(value, (int, float)):
            self._val = Decimal(str(value))
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                self._val = Decimal(0)
            else:
                try:
                    self._val = Decimal(stripped)
                except InvalidOperation:
                    raise ValueError(f"Big: cannot convert {value!r} to a number")
        else:
            # Last resort – try str conversion
            try:
                self._val = Decimal(str(value))
            except (InvalidOperation, TypeError):
                raise TypeError(
                    f"Big: unsupported type {type(value).__name__!r} for value {value!r}"
                )

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
        """Division.  ``x.div(y)``  Raises ``ZeroDivisionError`` on /0."""
        divisor = Big(other)._val
        if divisor == 0:
            raise ZeroDivisionError("Big: division by zero")
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
        return Big(-self._val)

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
        return Big(other).plus(self)

    def __sub__(self, other):
        return self.minus(other)

    def __rsub__(self, other):
        return Big(other).minus(self)

    def __mul__(self, other):
        return self.mul(other)

    def __rmul__(self, other):
        return Big(other).mul(self)

    def __truediv__(self, other):
        return self.div(other)

    def __rtruediv__(self, other):
        return Big(other).div(self)

    def __neg__(self):
        return Big(-self._val)

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
        return self._val != 0

    def __str__(self):
        return str(self._val)

    def __repr__(self):
        return f"Big({self._val})"

    def __hash__(self):
        return hash(self._val)
