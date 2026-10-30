"""Template context processors."""

from django.conf import settings


def site_settings(request):
    """Common template variables."""
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Петелька"),
        "ADMIN_URL": getattr(settings, "ADMIN_URL", "admin/"),
    }
