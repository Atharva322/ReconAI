from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


@dataclass(frozen=True, order=True)
class Money:
    """Same-currency money represented as integer minor units."""

    amount_cents: int
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount_cents, int):
            raise TypeError("amount_cents must be an integer")
        if self.amount_cents < 0:
            raise ValueError("money amounts cannot be negative in Phase 0")
        if self.currency != "USD":
            raise ValueError("Phase 0 supports USD only")

    @classmethod
    def parse(cls, value: str, currency: str = "USD") -> "Money":
        return cls(cents_from_decimal_string(value), currency)

    def to_decimal(self) -> Decimal:
        return (Decimal(self.amount_cents) / Decimal(100)).quantize(Decimal("0.01"))

    def to_api(self) -> dict[str, int | str]:
        return {"amount_cents": self.amount_cents, "currency": self.currency}

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        if other.amount_cents > self.amount_cents:
            raise ValueError("Phase 0 money subtraction cannot produce negative values")
        return Money(self.amount_cents - other.amount_cents, self.currency)

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount_cents + other.amount_cents, self.currency)

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError("currency mismatch")


def cents_from_decimal_string(value: str) -> int:
    try:
        amount = Decimal(value.replace("$", "").replace(",", "").strip())
    except (AttributeError, InvalidOperation) as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc

    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quantized < 0:
        raise ValueError("money amounts cannot be negative in Phase 0")
    return int(quantized * 100)
