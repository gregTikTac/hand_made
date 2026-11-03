"""Cart count for the header and the mobile navigation."""

from orders.cart import count, product_ids


def cart(request):
    return {
        "cart_count": count(request.session),
        "cart_ids": product_ids(request.session),
    }
