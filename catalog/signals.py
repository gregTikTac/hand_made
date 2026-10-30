"""Remove files from storage when rows are deleted (also on cascade / queryset.delete()).

``Model.delete()`` overrides are not called on cascades, signals are.
"""

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from catalog import images as image_utils
from catalog.models import Product, ProductImage


def _delete_file_on_commit(field_file) -> None:
    if field_file and field_file.name:
        storage, name = field_file.storage, field_file.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(post_delete, sender=ProductImage)
def delete_image_files(sender, instance, **kwargs):
    image, width = instance.image, instance.image_width
    if image and image.name:
        # Variants first (they are derived from the name), then the original.
        transaction.on_commit(lambda: image_utils.delete_variants(image, width))
        _delete_file_on_commit(image)


@receiver(post_delete, sender=Product)
def delete_product_files(sender, instance, **kwargs):
    _delete_file_on_commit(instance.materials_image)
    _delete_file_on_commit(instance.pdf_file)
