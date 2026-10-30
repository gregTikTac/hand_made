"""Shared pytest fixtures."""

import pytest
from django.core.files.storage import storages


@pytest.fixture(autouse=True)
def _isolated_media(tmp_path, settings):
    """Every test writes uploads into its own temp dir (public and private storages)."""
    from catalog.models import Product

    media = tmp_path / "media"
    private = tmp_path / "private_media"
    settings.MEDIA_ROOT = media
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(media), "base_url": "/media/"},
        },
        "private": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(private)},
        },
    }
    # Storages are cached per alias: drop them so the new settings apply.
    storages._storages.clear()
    # FileField resolved its storage callable at import time: point it at the fresh one.
    pdf_field = Product._meta.get_field("pdf_file")
    original_storage = pdf_field.storage
    pdf_field.storage = storages["private"]
    yield
    pdf_field.storage = original_storage
    storages._storages.clear()
