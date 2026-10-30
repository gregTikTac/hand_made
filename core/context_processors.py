"""Template context processors."""

from django.conf import settings


def site_settings(request):
    """Common template variables.

    ``CONTACT_LINKS`` comes from env until SiteSettings (editable in admin) arrives in stage 7;
    only links that are set are shown.
    """
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Петелька"),
        "ADMIN_URL": getattr(settings, "ADMIN_URL", "admin/"),
        "CONTACT_LINKS": [
            {"title": title, "url": url, "external": external}
            for title, url, external in (
                ("Поддержка", getattr(settings, "SUPPORT_URL", ""), False),
                ("VK", getattr(settings, "VK_URL", ""), True),
                ("Telegram", getattr(settings, "TELEGRAM_URL", ""), True),
                ("Instagram", getattr(settings, "INSTAGRAM_URL", ""), True),
            )
            if url
        ],
    }
