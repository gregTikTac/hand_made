"""Cart lines for the storefront: published products only, prices from get_price."""

from dataclasses import dataclass

from catalog.models import Product
from catalog.pricing import get_price
from orders import cart


@dataclass(frozen=True)
class CartLine:
    product: Product
    price: object


@dataclass(frozen=True)
class CartSummary:
    lines: list
    subtotal: int
    discount: int
    total: int

    @property
    def count(self) -> int:
        return len(self.lines)


def load_cart(session) -> CartSummary:
    """Drop ids that are no longer published. Prices are computed, never read from the session."""
    ids = cart.product_ids(session)
    products = {
        product.pk: product
        for product in Product.objects.published().with_images().filter(pk__in=ids)
    }
    kept = []
    lines = []
    for pk in ids:
        product = products.get(pk)
        if product is None:
            continue
        kept.append(pk)
        lines.append(CartLine(product=product, price=get_price(product)))
    if kept != ids:
        session[cart.CART_SESSION_KEY] = kept
        session.modified = True
    subtotal = sum((line.price.old or line.price.final) for line in lines)
    total = sum(line.price.final for line in lines)
    return CartSummary(lines=lines, subtotal=subtotal, discount=subtotal - total, total=total)
