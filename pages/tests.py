"""Smoke tests for static pages."""
from django.test import TestCase
from django.urls import reverse


class HomePageTestCase(TestCase):
    """Home page smoke test."""

    def test_home_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PDF-мастер-классы")
