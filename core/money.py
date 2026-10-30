"""Money helpers. All amounts are integer kopecks (never float), see .clinerules."""

from decimal import ROUND_HALF_UP, Decimal

KOPECKS_IN_RUBLE = 100
_NBSP = "\u00a0"


def rubles_to_kopecks(value: Decimal | int | str) -> int:
    """Convert rubles (Decimal/int/str) to integer kopecks, rounding half up to a kopeck."""
    amount = Decimal(value) * KOPECKS_IN_RUBLE
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def kopecks_to_rubles(kopecks: int) -> Decimal:
    """Convert integer kopecks to a Decimal amount of rubles."""
    return (Decimal(kopecks) / KOPECKS_IN_RUBLE).quantize(Decimal("0.01"))


def format_rub(kopecks: int | None) -> str:
    """Format kopecks for display: ``1 290 ₽`` (whole rubles) or ``1 290,50 ₽``."""
    if kopecks is None:
        return ""
    rubles, rest = divmod(int(kopecks), KOPECKS_IN_RUBLE)
    text = f"{rubles:,}".replace(",", _NBSP)
    if rest:
        text += f",{rest:02d}"
    return f"{text}{_NBSP}₽"
