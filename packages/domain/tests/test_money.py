import pytest

from reconai_domain import Money, cents_from_decimal_string


@pytest.mark.parametrize(
    ("raw", "expected_cents"),
    [
        ("0", 0),
        ("0.01", 1),
        ("18,450.00", 1_845_000),
        ("$17,200", 1_720_000),
        ("999999999.99", 99_999_999_999),
    ],
)
def test_money_parses_to_integer_cents(raw: str, expected_cents: int) -> None:
    assert cents_from_decimal_string(raw) == expected_cents


def test_money_api_round_trip_shape_is_exact() -> None:
    money = Money.parse("$18,450.00")

    assert money.to_api() == {"amount_cents": 1_845_000, "currency": "USD"}
    assert str(money.to_decimal()) == "18450.00"


def test_money_rejects_float_amounts() -> None:
    with pytest.raises(TypeError):
        Money(18450.00)  # type: ignore[arg-type]
