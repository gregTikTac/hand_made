"""Pricing tests: the table from ARCHITECTURE §3 is mandatory (ADR-0003)."""

import pytest

from catalog.factories import ProductFactory
from catalog.pricing import (
    BADGE_PREORDER,
    BADGE_SALE,
    SOURCE_BASE,
    SOURCE_CAMPAIGN,
    SOURCE_PREORDER,
    apply_percent,
    calculate_price,
    get_price,
)

RUB = 100  # kopecks in a ruble


@pytest.mark.parametrize(
    ("base", "campaign", "preorder", "final", "old", "badges"),
    [
        (600, None, None, 600, None, ()),
        (600, 30, None, 420, 600, (BADGE_SALE,)),
        (600, None, 20, 480, 600, (BADGE_PREORDER,)),
        (600, 30, 20, 420, 600, (BADGE_PREORDER, BADGE_SALE)),
        (590, 30, None, 413, 590, (BADGE_SALE,)),
    ],
)
def test_architecture_table(base, campaign, preorder, final, old, badges):
    info = calculate_price(base * RUB, campaign_percent=campaign, preorder_percent=preorder)
    assert info.final == final * RUB
    assert info.old == (old * RUB if old else None)
    assert info.badges == badges


def test_larger_discount_wins_and_discounts_do_not_stack():
    info = calculate_price(600 * RUB, campaign_percent=10, preorder_percent=30)
    assert info.final == 420 * RUB  # 30%, not 37%
    assert info.source == SOURCE_PREORDER
    assert info.discount_percent == 30


def test_equal_discounts_attributed_to_campaign():
    info = calculate_price(600 * RUB, campaign_percent=20, preorder_percent=20)
    assert info.final == 480 * RUB
    assert info.source == SOURCE_CAMPAIGN


def test_rounds_down_to_whole_rubles():
    # 333 ₽ − 30% = 233.1 ₽ -> 233 ₽
    assert apply_percent(333 * RUB, 30) == 233 * RUB
    # 449,99 ₽ − 10% = 404.991 -> 404 ₽
    assert apply_percent(44999, 10) == 404 * RUB


def test_no_discount_returns_base_and_no_old_price():
    info = calculate_price(45000)
    assert (info.final, info.old, info.source, info.has_discount) == (
        45000,
        None,
        SOURCE_BASE,
        False,
    )


def test_compare_price_shown_as_old_price_without_discount():
    info = calculate_price(45000, 60000)
    assert info.final == 45000
    assert info.old == 60000
    assert info.has_discount is True


def test_compare_price_not_greater_than_base_is_ignored():
    assert calculate_price(45000, 45000).old is None
    assert calculate_price(45000, 30000).old is None


def test_discount_uses_base_as_old_price_not_compare_price():
    info = calculate_price(45000, 60000, campaign_percent=30)
    assert info.old == 45000
    assert info.final == 31500


def test_preorder_without_discount_keeps_badge_only():
    info = calculate_price(45000, preorder_percent=0)
    assert info.final == 45000
    assert info.badges == (BADGE_PREORDER,)
    assert info.source == SOURCE_PREORDER


def test_integer_money_only():
    info = calculate_price(45000, campaign_percent=30)
    assert isinstance(info.final, int)
    assert isinstance(info.old, int)


@pytest.mark.parametrize("percent", [-1, 101])
def test_invalid_percent_rejected(percent):
    with pytest.raises(ValueError):
        apply_percent(45000, percent)


def test_non_positive_base_rejected():
    with pytest.raises(ValueError):
        calculate_price(0)


@pytest.mark.django_db
def test_get_price_uses_product_prices():
    product = ProductFactory(base_price=59000, compare_price=70000)
    info = get_price(product)
    assert info.final == 59000
    assert info.old == 70000
