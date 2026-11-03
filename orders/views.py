"""Cart and guest checkout. Payment starts in stage 4; here the order is only created."""

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from catalog.models import Product
from orders import cart
from orders.forms import CheckoutForm
from orders.selectors import load_cart
from orders.services import PriceChangedError, parse_seen, place_order, prices_match, seen_token

LAST_ORDER_SESSION_KEY = "last_order_id"


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def cart_page(request):
    summary = load_cart(request.session)
    form = CheckoutForm()
    return render(
        request,
        "orders/cart.html",
        {
            "summary": summary,
            "form": form,
            "seen_token": seen_token(summary.lines),
            "price_changed": False,
        },
    )


@require_POST
def add(request, product_id):
    product = get_object_or_404(Product.objects.published(), pk=product_id)
    cart.add(request.session, product.pk)
    if request.headers.get("HX-Request"):
        button_css = request.POST.get("css", "")
        if button_css not in {"btn btn--sm", "btn btn--block", "btn"}:
            button_css = "btn btn--sm"
        return render(request, "orders/_added.html", {"button_css": button_css})
    return redirect("orders:cart")


@require_POST
def remove(request, product_id):
    cart.remove(request.session, product_id)
    summary = load_cart(request.session)
    if request.headers.get("HX-Request"):
        return render(
            request,
            "orders/_cart_body.html",
            {
                "summary": summary,
                "form": CheckoutForm(),
                "seen_token": seen_token(summary.lines),
                "price_changed": False,
                "oob": True,
            },
        )
    return redirect("orders:cart")


@ratelimit(key="ip", rate="8/m", method="POST", block=False)
def checkout(request):
    """Create the order. A second submit is required when a price moved since the page was rendered."""
    if request.method != "POST":
        return redirect("orders:cart")
    summary = load_cart(request.session)
    if not summary.lines:
        return redirect("orders:cart")
    if getattr(request, "limited", False):
        form = CheckoutForm(request.POST)
        return render(
            request,
            "orders/cart.html",
            {
                "summary": summary,
                "form": form,
                "seen_token": seen_token(summary.lines),
                "price_changed": False,
                "rate_limited": True,
            },
            status=429,
        )

    form = CheckoutForm(request.POST)
    seen = parse_seen(request.POST.get("seen", ""))
    changed = form.is_valid() and not prices_match(summary.lines, seen)
    if not form.is_valid() or changed:
        return render(
            request,
            "orders/cart.html",
            {
                "summary": summary,
                "form": form,
                "seen_token": seen_token(summary.lines),
                "price_changed": changed,
            },
        )

    products = [line.product for line in summary.lines]
    try:
        order = place_order(
            products=products,
            seen=seen,
            email=form.cleaned_data["email"],
            marketing=False,
            ip=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except PriceChangedError:
        summary = load_cart(request.session)
        return render(
            request,
            "orders/cart.html",
            {
                "summary": summary,
                "form": form,
                "seen_token": seen_token(summary.lines),
                "price_changed": True,
            },
        )

    cart.clear(request.session)
    request.session[LAST_ORDER_SESSION_KEY] = str(order.pk)
    return redirect("orders:done")


def done(request):
    from orders.models import Order

    order_id = request.session.get(LAST_ORDER_SESSION_KEY)
    order = Order.objects.filter(pk=order_id).first() if order_id else None
    if order is None:
        return redirect("orders:cart")
    return render(request, "orders/done.html", {"order": order})
