"""Placing an order and moving it through the payment state machine.

Stage 3 only creates orders in ``created``. ``transition`` is the single door
for later status changes (payment webhooks, stage 4).
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from catalog.pricing import get_price
from orders.models import OFFER_VERSION, PDN_VERSION, Order, OrderItem


class PriceChangedError(Exception):
    """The price on screen is not the price we would charge right now."""


class InvalidTransitionError(Exception):
    """This status cannot take this event."""


# (status, event) -> new status. See ARCHITECTURE §4.
TRANSITIONS = {
    ("created", "pay"): Order.Status.PENDING,
    ("pending", "succeeded"): Order.Status.PAID,
    ("pending", "canceled"): Order.Status.CANCELED,
    ("pending", "timeout"): Order.Status.EXPIRED,
    ("paid", "files_sent"): Order.Status.FULFILLED,
    ("paid", "preorder"): Order.Status.AWAITING_RELEASE,
    ("paid", "refund"): Order.Status.REFUNDED,
    ("awaiting_release", "release"): Order.Status.FULFILLED,
    ("awaiting_release", "refund"): Order.Status.REFUNDED,
}


def seen_token(lines) -> str:
    """Hidden-field value: the prices the customer is looking at, ``id:kopecks``."""
    return ",".join(f"{line.product.pk}:{line.price.final}" for line in lines)


def parse_seen(raw: str) -> dict[int, int]:
    found: dict[int, int] = {}
    for part in (raw or "").split(","):
        if ":" not in part:
            continue
        pk, price = part.split(":", 1)
        try:
            found[int(pk)] = int(price)
        except ValueError:
            continue
    return found


def prices_match(lines, seen: dict[int, int]) -> bool:
    return all(seen.get(line.product.pk) == line.price.final for line in lines)


def transition(order: Order, event: str) -> Order:
    """Move ``order`` along an allowed edge. Anything else raises."""
    new_status = TRANSITIONS.get((order.status, event))
    if new_status is None:
        raise InvalidTransitionError(f"{order.status} + {event}")
    order.status = new_status
    update_fields = ["status", "updated_at"]
    if new_status == Order.Status.PAID:
        order.paid_at = timezone.now()
        update_fields.append("paid_at")
    order.save(update_fields=update_fields)
    return order


def _next_number(moment) -> str:
    prefix = f"K-{moment.year}-"
    last = (
        Order.objects.select_for_update()
        .filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:06d}"


@transaction.atomic
def place_order(*, products, seen: dict[int, int], email: str, marketing: bool, ip, user_agent):
    """Snapshot current prices into a ``created`` order. Raises PriceChanged if ``seen`` is stale."""
    now = timezone.now()
    items = []
    subtotal = 0
    total = 0
    for product in products:
        price = get_price(product, now)
        if seen.get(product.pk) != price.final:
            raise PriceChangedError(product.pk)
        items.append((product, price))
        subtotal += price.old or price.final
        total += price.final

    for _attempt in range(3):
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    number=_next_number(now),
                    email=email,
                    status=Order.Status.CREATED,
                    subtotal=subtotal,
                    discount_total=subtotal - total,
                    total=total,
                    consent_offer_at=now,
                    consent_pdn_at=now,
                    offer_version=OFFER_VERSION,
                    pdn_version=PDN_VERSION,
                    marketing_consent=marketing,
                    ip=ip,
                    user_agent=(user_agent or "")[:400],
                )
            break
        except IntegrityError:
            continue
    else:
        raise IntegrityError("Could not allocate an order number")

    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=product,
                title=product.title,
                unit_price=price.final,
                price_source=price.source,
            )
            for product, price in items
        ]
    )
    return order
