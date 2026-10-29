"""Тонкая обёртка над переменными окруженияения."""
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class Env:
    """Lightweight env reader with type casts."""

    def __init__(self):
        self._raw = os.environ

    def __call__(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    def bool(self, key: str, default: bool = False) -> bool:
        value = self._raw.get(key)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def int(self, key: str, default: int = 0) -> int:
        value = self._raw.get(key)
        if value is None:
            return default
        return int(value)

    def list(self, key: str, default: list | None = None) -> list:
        value = self._raw.get(key)
        if value is None or value == "":
            return default or []
        return [item.strip() for item in value.split(",") if item.strip()]

    def db_url(self, key: str, default: dict | None = None) -> dict:
        import dj_database_url  # noqa: F401

        url = self._raw.get(key)
        if not url:
            return default or {}
        return dj_database_url.parse(url)


env = Env()
