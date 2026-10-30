"""Fill the database with demo products (dev/staging only) — DoD: 80+ products on dev.

* First four products come from ``docs/brief/sample-products.csv`` (real titles/prices).
* The rest are generated (~every 9th is a combo). Photos are generated placeholders (Pillow).
* Idempotent: products are matched by slug; existing ones are left untouched.
"""

import csv
import random
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw

from catalog.models import Category, Product, ProductImage, ProductVideo

SAMPLE_CSV = Path(settings.BASE_DIR) / "docs" / "brief" / "sample-products.csv"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
ANIMALS = ["Зайка", "Мишка", "Слонёнок", "Котёнок", "Пёсик", "Ёжик", "Совушка", "Единорог", "Панда"]
PALETTES = [
    ((234, 217, 198), (216, 191, 166)),
    ((240, 226, 228), (217, 179, 186)),
    ((230, 226, 211), (201, 193, 165)),
    ((242, 232, 218), (226, 205, 180)),
]
VIDEO_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://rutube.ru/video/0123456789abcdef0123456789abcdef/",
    "https://vk.com/video-12345_67890",
]


def placeholder(title: str, palette, size=(900, 1125)) -> bytes:
    """Vertical 4:5 gradient with a burgundy blob — enough to check the layout."""
    top, bottom = palette
    image = Image.new("RGB", size, top)
    draw = ImageDraw.Draw(image)
    for y in range(size[1]):
        ratio = y / size[1]
        color = tuple(round(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (size[0], y)], fill=color)
    draw.ellipse(
        [size[0] * 0.25, size[1] * 0.28, size[0] * 0.75, size[1] * 0.68], fill=(142, 26, 46)
    )
    draw.text((size[0] * 0.08, size[1] * 0.85), title[:40], fill=(46, 36, 32))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Создать демо-товары (по умолчанию 84) с картинками-заглушками и PDF."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=84, help="Сколько товаров всего")
        parser.add_argument(
            "--seed", type=int, default=2026, help="Seed генератора (повторяемость)"
        )

    def handle(self, *args, count, seed, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo запускается только при DEBUG=True (dev/staging).")
        if count < 1:
            raise CommandError("--count должен быть положительным")
        rng = random.Random(seed)
        self.beginner, _ = Category.objects.get_or_create(
            slug="dlya-nachinayushchikh", defaults={"title": "Для начинающих", "position": 1}
        )
        created = 0
        for index, row in enumerate(self._rows(count, rng)):
            if Product.objects.filter(slug=row["slug"]).exists():
                continue
            self._create(index, row, rng)
            created += 1
        self.stdout.write(
            self.style.SUCCESS(f"Создано: {created}. Всего товаров: {Product.objects.count()}.")
        )

    def _rows(self, count, rng):
        rows = []
        if SAMPLE_CSV.exists():
            with SAMPLE_CSV.open(encoding="utf-8", newline="") as handle:
                rows.extend(csv.DictReader(handle))
        rows = rows[:count]
        number = len(rows)
        while len(rows) < count:
            number += 1
            rows.append(
                {
                    "slug": f"demo-{number}",
                    "title": f"Мастер-класс «{ANIMALS[number % len(ANIMALS)]} {number}»",
                    "base_price": str(rng.choice([35000, 40000, 45000, 50000, 60000, 75000])),
                    "category": "combo" if number % 9 == 0 else "single",
                    "height_cm": str(rng.choice([15, 20, 25, 30])),
                    "videos_count": str(rng.choice([0, 1, 3])),
                    "description": "Подробный мастер-класс с фото процесса вязания и сборки. "
                    "Моя поддержка на любом этапе вязания!",
                    "construction": "",
                    "clothing_included": "no",
                }
            )
        return rows

    def _create(self, index, row, rng):
        product = Product(
            slug=row["slug"],
            title=row["title"],
            base_price=int(row["base_price"]),
            is_combo=row.get("category") == "combo",
            height_cm=int(row["height_cm"]) if row.get("height_cm") else None,
            length_cm=int(row["length_cm"]) if row.get("length_cm") else None,
            videos_count=int(row.get("videos_count") or 0),
            construction=row.get("construction", ""),
            clothing_included=row.get("clothing_included") == "yes",
            description=row.get("description", ""),
            status=Product.Status.PUBLISHED,
            sort_order=index,
            popularity=rng.randint(0, 1000),
        )
        product.pdf_file.save("demo.pdf", ContentFile(PDF_BYTES), save=False)
        product.save()
        if rng.random() < 0.3:
            product.categories.add(self.beginner)

        palette = PALETTES[index % len(PALETTES)]
        for position in range(rng.randint(2, 5)):
            shade = tuple(min(255, c + position * 6) for c in palette[0])
            ProductImage(
                product=product,
                position=position,
                is_cover=position == 0,
                alt=f"{product.title}, фото {position + 1}",
                image=ContentFile(
                    placeholder(product.title, (shade, palette[1])),
                    name=f"demo-{product.slug}-{position}.jpg",
                ),
            ).save()
        if index % 3 == 0:
            ProductVideo.objects.create(product=product, url=VIDEO_URLS[index % len(VIDEO_URLS)])
