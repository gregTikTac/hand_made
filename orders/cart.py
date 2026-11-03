"""Session cart. Only product ids are stored; prices are recalculated on every view."""

CART_SESSION_KEY = "cart"


def product_ids(session) -> list[int]:
    raw = session.get(CART_SESSION_KEY) or []
    return [int(pk) for pk in raw]


def count(session) -> int:
    return len(product_ids(session))


def add(session, product_id: int) -> None:
    """One copy of a digital product. Adding it again does nothing."""
    current = product_ids(session)
    if product_id not in current:
        current.append(product_id)
    session[CART_SESSION_KEY] = current
    session.modified = True


def remove(session, product_id: int) -> None:
    session[CART_SESSION_KEY] = [pk for pk in product_ids(session) if pk != product_id]
    session.modified = True


def clear(session) -> None:
    session[CART_SESSION_KEY] = []
    session.modified = True
