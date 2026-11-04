"""Price calculation — the single source of truth for prices (ADR-0003).

All amounts are integer kopecks. Rules (ARCHITECTURE §3):
1. Preorder discount and campaign discount do NOT stack: the larger one wins.
2. The "old price" is the base price (computed, never stored); without a discount
   a manual ``compare_price`` (> base) is shown as the old price.
3. Rounding: down to whole rubles.

Campaigns and preorders arrive in stage 6; until then ``get_price`` has no active
discounts, but the arithmetic below is complete and covered by tests.
"""

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from core.money import KOPECKS_IN_RUBLE

SOURCE_BASE = "base"
SOURCE_CAMPAIGN = "campaign"
SOURCE_PREORDER = "preorder"

BADGE_SALE = "sale"
BADGE_PREORDER = "preorder"


@dataclass(frozen=True)
class PriceInfo:
    """Result of a price calculation."""

    final: int  # kopecks the customer pays
    old: int | None  # struck-through price, kopecks
    source: str  # base | campaign | preorder
    badges: tuple[str, ...] = ()  # "preorder" first, then "sale"
    discount_percent: int = 0  # percent actually applied
    campaign_id: int | None = None
    release_date: datetime | None = None

    @property
    def has_discount(self) -> bool:
        return self.final < (self.old or 0)

    @property
    def is_sale(self) -> bool:
        return BADGE_SALE in self.badges

    @property
    def is_preorder(self) -> bool:
        return BADGE_PREORDER in self.badges


def apply_percent(base: int, percent: int) -> int:
    """Price after a percent discount, rounded down to whole rubles (kopecks result)."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be within 0..100")
    discounted = base * (100 - percent) // 100
    return discounted // KOPECKS_IN_RUBLE * KOPECKS_IN_RUBLE


def calculate_price(
    base: int,
    compare: int | None = None,
    *,
    campaign_percent: int | None = None,
    preorder_percent: int | None = None,
) -> PriceInfo:
    """Pure price function.

    ``campaign_percent`` is the active campaign discount (None — no campaign).
    ``preorder_percent`` is the preorder discount (None — not a preorder in sales window).
    """
    if base <= 0:
        raise ValueError("base price must be positive")

    badges: list[str] = []
    if preorder_percent is not None:
        badges.append(BADGE_PREORDER)
    if campaign_percent:
        badges.append(BADGE_SALE)

    campaign = campaign_percent or 0
    preorder = preorder_percent or 0
    percent = max(campaign, preorder)

    if percent > 0:
        source = SOURCE_CAMPAIGN if campaign >= preorder else SOURCE_PREORDER
        return PriceInfo(
            final=apply_percent(base, percent),
            old=base,
            source=source,
            badges=tuple(badges),
            discount_percent=percent,
        )

    old = compare if compare and compare > base else None
    source = SOURCE_PREORDER if preorder_percent is not None else SOURCE_BASE
    return PriceInfo(final=base, old=old, source=source, badges=tuple(badges))


def get_price(
    product, now: datetime | None = None, *, release=None, campaign=None, _lookup=True
) -> PriceInfo:
    """Price of a product at moment ``now``.

    ``attach_prices`` passes the campaign and preorder it already loaded.
    A direct call looks them up itself.
    """
    now = now or timezone.now()
    if _lookup:
        campaign_percent, campaign_id, preorder_percent, release_date = _offers(product, now)
    else:
        campaign_percent, campaign_id, preorder_percent, release_date = _from_loaded(
            release, campaign, now
        )
    info = calculate_price(
        product.base_price,
        product.compare_price,
        campaign_percent=campaign_percent,
        preorder_percent=preorder_percent,
    )
    applied_campaign = campaign_id if info.source == SOURCE_CAMPAIGN else None
    return PriceInfo(
        final=info.final,
        old=info.old,
        source=info.source,
        badges=info.badges,
        discount_percent=info.discount_percent,
        campaign_id=applied_campaign,
        release_date=release_date if preorder_percent is not None else None,
    )


def _offers(product, now: datetime):
    from promo.models import DiscountCampaign, PreorderRelease

    release = PreorderRelease.objects.filter(product_id=product.pk).first()
    campaign = (
        DiscountCampaign.objects.filter(is_active=True, starts_at__lte=now, ends_at__gt=now)
        .order_by("-percent")
        .first()
    )
    return _from_loaded(release, campaign, now)


def _from_loaded(release, campaign, now: datetime):
    from promo.models import PreorderRelease

    preorder_percent = None
    release_date = None
    in_window = False
    if (
        release
        and release.status
        in (
            PreorderRelease.Status.SCHEDULED,
            PreorderRelease.Status.SELLING,
        )
        and release.sales_start <= now <= release.sales_end
    ):
        preorder_percent = release.discount_percent
        release_date = release.release_date
        in_window = True

    campaign_percent = None
    campaign_id = None
    if campaign and not (campaign.exclude_preorders and in_window):
        campaign_percent = campaign.percent
        campaign_id = campaign.pk
    return campaign_percent, campaign_id, preorder_percent, release_date
