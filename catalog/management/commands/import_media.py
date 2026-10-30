"""Attach photos / materials photo / PDF from a folder tree to existing products by slug.

Expected layout (``--source``)::

    <source>/<slug>/photos/*.jpg|png|webp   -> ProductImage (sorted by file name; first = cover)
    <source>/<slug>/materials.(jpg|png|webp) -> Product.materials_image
    <source>/<slug>/*.pdf                    -> Product.pdf_file (the only PDF in the folder)

The command is idempotent: a photo already attached (same file name stored in ``alt``) is skipped,
an existing PDF / materials photo is replaced only with ``--overwrite``.
"""

import logging
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Product, ProductImage

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def natural_key(path: Path):
    """Sort photo_2 before photo_10."""
    import re

    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


class Command(BaseCommand):
    help = "Прикрепить фото и PDF из папок <source>/<slug>/ к товарам (по slug)."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="Папка с подпапками по slug")
        parser.add_argument(
            "--overwrite", action="store_true", help="Заменять PDF и фото материалов"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Только показать, что будет сделано"
        )

    def handle(self, *args, source, overwrite, dry_run, **options):
        root = Path(source)
        if not root.is_dir():
            raise CommandError(f"Папка не найдена: {root}")

        folders = sorted(path for path in root.iterdir() if path.is_dir())
        if not folders:
            raise CommandError(f"В {root} нет подпапок с товарами")

        totals = {"products": 0, "photos": 0, "pdf": 0, "materials": 0, "missing": 0}
        for folder in folders:
            product = Product.objects.filter(slug=folder.name).first()
            if product is None:
                self.stdout.write(
                    self.style.WARNING(f"Нет товара со slug «{folder.name}» — пропуск")
                )
                totals["missing"] += 1
                continue
            totals["products"] += 1
            self._process(product, folder, overwrite=overwrite, dry_run=dry_run, totals=totals)

        self.stdout.write(
            self.style.SUCCESS(
                "Готово: товаров {products}, фото {photos}, PDF {pdf}, материалов {materials}, "
                "не найдено товаров {missing}".format(**totals)
                + (" (dry-run, ничего не записано)" if dry_run else "")
            )
        )

    def _process(self, product, folder: Path, *, overwrite, dry_run, totals):
        photos_dir = folder / "photos"
        photos = (
            sorted(
                (p for p in photos_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES),
                key=natural_key,
            )
            if photos_dir.is_dir()
            else []
        )
        known = set(product.images.values_list("alt", flat=True))
        has_cover = product.images.filter(is_cover=True).exists()
        next_position = product.images.count()

        for index, photo in enumerate(photos):
            marker = photo.name
            if marker in known:
                continue
            totals["photos"] += 1
            self.stdout.write(f"  {product.slug}: фото {photo.name}")
            if dry_run:
                continue
            with photo.open("rb") as handle:
                ProductImage(
                    product=product,
                    alt=marker,
                    position=next_position + index,
                    is_cover=not has_cover and index == 0,
                    image=File(handle, name=photo.name),
                ).save()
            has_cover = True

        materials = next(
            (
                p
                for p in folder.iterdir()
                if p.stem.lower() == "materials" and p.suffix.lower() in IMAGE_SUFFIXES
            ),
            None,
        )
        if materials and (overwrite or not product.materials_image):
            totals["materials"] += 1
            self.stdout.write(f"  {product.slug}: фото материалов {materials.name}")
            if not dry_run:
                with materials.open("rb") as handle:
                    product.materials_image.save(materials.name, File(handle), save=False)
                    product.save(
                        update_fields=[
                            "materials_image",
                            "materials_image_width",
                            "materials_image_height",
                        ]
                    )

        pdfs = sorted(folder.glob("*.pdf"))
        if len(pdfs) > 1:
            self.stdout.write(
                self.style.WARNING(f"  {product.slug}: несколько PDF, взят {pdfs[0].name}")
            )
        if pdfs and (overwrite or not product.pdf_file):
            totals["pdf"] += 1
            self.stdout.write(f"  {product.slug}: PDF {pdfs[0].name}")
            if not dry_run:
                with pdfs[0].open("rb") as handle:
                    product.pdf_file.save(pdfs[0].name, File(handle), save=False)
                    product.save(update_fields=["pdf_file"])
