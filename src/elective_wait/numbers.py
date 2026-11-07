"""Rounding and year labels shared by the page and the tests."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float, places: int) -> float:
    quant = Decimal("1") if places == 0 else Decimal(10) ** -places
    rounded = Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    return float(rounded)


def year_label(financial_year: str) -> str:
    return financial_year.replace("-", "–", 1)


def people(value: float) -> str:
    return f"{int(round_half_up(value, 0)):,}"


def pct(value: float) -> str:
    rounded = round_half_up(value, 1)
    if rounded in (0, 100):
        return f"{int(rounded)}%"
    return f"{rounded:.1f}%"
