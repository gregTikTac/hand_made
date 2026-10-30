"""Text helpers."""

from django.utils.text import slugify

_RU_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
}  # fmt: skip


def slugify_ru(value: str) -> str:
    """Transliterate Russian text to an ASCII URL slug: «Козлёнок Боря» -> kozlyonok-borya."""
    transliterated = "".join(_RU_TO_LAT.get(char, char) for char in value.lower())
    return slugify(transliterated)


def unique_slug(model, base: str, *, max_length: int, exclude_pk=None, field: str = "slug") -> str:
    """Return a slug based on ``base`` that is unique for ``model`` (adds -2, -3, ... if taken)."""
    base = (slugify_ru(base) or "item")[:max_length].strip("-") or "item"
    candidate, counter = base, 1
    queryset = model._default_manager.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    while queryset.filter(**{field: candidate}).exists():
        counter += 1
        suffix = f"-{counter}"
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
    return candidate
