"""factory_boy factories for tests and the demo seed command."""

from io import BytesIO

import factory
from django.core.files.base import ContentFile
from PIL import Image

from catalog.models import Category, Product, ProductImage, ProductVideo

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def make_image_bytes(
    width: int = 800, height: int = 1000, color=(200, 150, 140), fmt: str = "JPEG"
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format=fmt)
    return buffer.getvalue()


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    title = factory.Sequence(lambda n: f"Категория {n}")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    title = factory.Sequence(lambda n: f"Мастер-класс «Игрушка {n}»")
    base_price = 45000
    status = Product.Status.PUBLISHED
    pdf_file = factory.LazyFunction(lambda: ContentFile(MINIMAL_PDF, name="schema.pdf"))


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage

    product = factory.SubFactory(ProductFactory)
    image = factory.LazyFunction(lambda: ContentFile(make_image_bytes(), name="photo.jpg"))
    position = factory.Sequence(lambda n: n)


class ProductVideoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVideo

    product = factory.SubFactory(ProductFactory)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
