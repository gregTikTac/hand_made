"""Template context processors."""

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format


def _row():
    try:
        from pages.models import SiteSettings

        return SiteSettings.objects.filter(pk=1).first()
    except (OperationalError, ProgrammingError):
        return None


def _banner(row):
    if row and row.banner_text:
        return row.banner_text
    try:
        from promo.models import DiscountCampaign

        now = timezone.now()
        campaign = DiscountCampaign.objects.filter(
            is_active=True, starts_at__lte=now, ends_at__gt=now
        ).first()
    except (OperationalError, ProgrammingError):
        return ""
    if not campaign:
        return ""
    end = date_format(timezone.localtime(campaign.ends_at), "j E")
    return f"{campaign.title}: −{campaign.percent}% до {end}"


def _legal():
    slots = {"offer": "offer", "privacy": "privacy", "pdn-consent": "pdn", "about": "about"}
    found = {"offer": "#", "privacy": "#", "pdn": "#", "about": "#about"}
    try:
        from pages.models import Page

        for page in Page.objects.filter(is_published=True):
            slot = slots.get(page.slug)
            if slot:
                found[slot] = reverse("page", args=[page.slug])
    except (OperationalError, ProgrammingError):
        pass
    return found


def site_settings(request):
    """Shop name, contacts and legal links. Admin values win once the row exists."""
    row = _row()
    legal_name = (row.legal_name if row and row.legal_name else None) or settings.LEGAL_NAME
    contacts = (
        ("Поддержка", row.support_url if row else settings.SUPPORT_URL, True),
        ("VK", row.vk_url if row else settings.VK_URL, True),
        ("Telegram", row.telegram_url if row else settings.TELEGRAM_URL, True),
        ("Instagram", row.instagram_url if row else settings.INSTAGRAM_URL, True),
    )
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Екатерина Зуева"),
        "LEGAL_NAME": legal_name,
        "ADMIN_URL": getattr(settings, "ADMIN_URL", "admin/"),
        "PROMO_BANNER": _banner(row),
        "legal_pages": _legal(),
        "CONTACT_LINKS": [
            {"title": title, "url": url, "external": external}
            for title, url, external in contacts
            if url
        ],
    }
