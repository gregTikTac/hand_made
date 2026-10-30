"""Storage accessors usable in model fields (callables are serialized by reference in migrations)."""

from django.core.files.storage import storages


def get_private_storage():
    """Private storage for purchased PDFs (never served directly, see ADR-0004)."""
    return storages["private"]
