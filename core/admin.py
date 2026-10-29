"""Unfold admin site configuration."""
from unfold.sites import UnfoldAdminSite


class KnittingAdminSite(UnfoldAdminSite):
    site_title = "Петелька"
    site_header = "Петелька — админка"
    index_title = "Добро пожаловать"


admin_site = KnittingAdminSite(name="knitting_admin")

