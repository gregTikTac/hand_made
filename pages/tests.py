"""Smoke tests for static pages."""

from django.test import TestCase
from django.urls import reverse

from catalog.factories import ProductImageFactory


class StaticAssetsTestCase(TestCase):
    """Every css/js file referenced by the base template must be resolvable by staticfiles."""

    def test_assets_are_found_by_staticfiles_finders(self):
        from django.contrib.staticfiles import finders

        for path in (
            "css/tokens.css",
            "css/components.css",
            "js/vendor/htmx.min.js",
            "js/vendor/alpine.min.js",
        ):
            self.assertIsNotNone(finders.find(path), f"static file not found: {path}")


class HomePageTestCase(TestCase):
    """Home page smoke test."""

    def test_home_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PDF-мастер-классы")
        self.assertContains(response, "Baloo Hand")
        self.assertContains(response, "<em>Hand</em>")
        self.assertContains(response, 'id="intro"')
        self.assertNotContains(response, "Петелька")
        self.assertNotContains(response, "Baloo_Hand")

    def test_home_hero_uses_popular_cover(self):
        image = ProductImageFactory(is_cover=True, product__popularity=50, product__title="Лисичка")
        response = self.client.get(reverse("home"))
        self.assertContains(response, image.image.url)
        self.assertContains(response, "Лисичка")
