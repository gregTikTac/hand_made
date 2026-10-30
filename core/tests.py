"""Tests for the project skeleton: env helper, storages, admin."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import TestCase
from django.urls import reverse

from config.env import Env


class EnvTestCase(TestCase):
    """config.env.Env type casts."""

    def test_casts(self):
        env = Env()
        env._raw = {"B": "True", "I": "7", "L": "a, b,,c", "DB": "sqlite:///x.sqlite3"}
        self.assertTrue(env.bool("B"))
        self.assertFalse(env.bool("MISSING", default=False))
        self.assertEqual(env.int("I"), 7)
        self.assertEqual(env.list("L"), ["a", "b", "c"])
        self.assertEqual(env.list("MISSING"), [])
        self.assertEqual(env.db_url("DB")["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(
            env.db_url("MISSING", default="sqlite:///y.sqlite3")["ENGINE"],
            "django.db.backends.sqlite3",
        )


class StoragesTestCase(TestCase):
    """Public and private storages are separate (ADR-0004)."""

    def test_private_storage_is_separate(self):
        self.assertIn("private", settings.STORAGES)
        public, private = storages["default"], storages["private"]
        self.assertNotEqual(public.location, private.location)

    def test_private_storage_roundtrip(self):
        private = storages["private"]
        name = private.save("tests/hello.txt", ContentFile(b"hello"))
        try:
            self.assertTrue(private.exists(name))
        finally:
            private.delete(name)


class AdminTestCase(TestCase):
    """Admin is reachable and protected."""

    def test_admin_redirects_anonymous_to_login(self):
        response = self.client.get(f"/{settings.ADMIN_URL}")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_admin_index_for_superuser(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_superuser("admin", "a@example.com", "pass12345")
        self.client.force_login(user)
        response = self.client.get(f"/{settings.ADMIN_URL}")
        self.assertEqual(response.status_code, 200)

    def test_home_url_resolves(self):
        self.assertEqual(reverse("home"), "/")
