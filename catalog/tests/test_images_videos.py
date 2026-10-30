"""Image variants (webp/srcset) and video model behaviour."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from PIL import Image

from catalog.factories import ProductImageFactory, ProductVideoFactory, make_image_bytes
from catalog.models import ProductImage
from catalog.video import VideoUrlError

pytestmark = pytest.mark.django_db


class TestImages:
    def test_webp_variants_generated_with_dimensions(self):
        image = ProductImageFactory(image=ContentFile(make_image_bytes(1200, 1500), name="big.jpg"))
        assert (image.image_width, image.image_height) == (1200, 1500)
        for width in (360, 720, 1080):
            assert storages["default"].exists(f"{image.image.name}.{width}.webp")
        assert "360w" in image.srcset and "720w" in image.srcset and "1080w" in image.srcset

    def test_small_image_is_not_upscaled(self):
        image = ProductImageFactory(image=ContentFile(make_image_bytes(500, 600), name="s.jpg"))
        storage = storages["default"]
        assert storage.exists(f"{image.image.name}.360.webp")
        assert storage.exists(f"{image.image.name}.500.webp")
        assert not storage.exists(f"{image.image.name}.720.webp")
        assert "720w" not in image.srcset

    def test_png_with_alpha_is_converted(self):
        buffer = BytesIO()
        Image.new("RGBA", (400, 500), (255, 0, 0, 128)).save(buffer, format="PNG")
        image = ProductImageFactory(image=ContentFile(buffer.getvalue(), name="a.png"))
        assert storages["default"].exists(f"{image.image.name}.360.webp")

    def test_delete_removes_files_and_variants(self, django_capture_on_commit_callbacks):
        image = ProductImageFactory()
        name = image.image.name
        with django_capture_on_commit_callbacks(execute=True):
            image.delete()
        assert not storages["default"].exists(name)
        assert not storages["default"].exists(f"{name}.360.webp")

    def test_files_survive_until_commit(self, django_capture_on_commit_callbacks):
        """A rolled-back deletion must not lose files: removal is deferred to on_commit."""
        image = ProductImageFactory()
        name = image.image.name
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            image.delete()
        assert callbacks
        assert storages["default"].exists(name)

    def test_cascade_delete_of_product_removes_all_files(self, django_capture_on_commit_callbacks):
        image = ProductImageFactory()
        product = image.product
        names = [image.image.name, f"{image.image.name}.720.webp", product.pdf_file.name]
        with django_capture_on_commit_callbacks(execute=True):
            product.delete()
        assert not storages["default"].exists(names[0])
        assert not storages["default"].exists(names[1])
        assert not storages["private"].exists(names[2])

    def test_replacing_file_removes_old_one(self):
        image = ProductImageFactory()
        storage = storages["default"]
        old_name = image.image.name
        image.image = ContentFile(make_image_bytes(900, 900), name="new.jpg")
        image.save()
        assert image.image.name != old_name
        assert not storage.exists(old_name)
        assert not storage.exists(f"{old_name}.360.webp")
        assert storage.exists(f"{image.image.name}.360.webp")

    def test_not_an_image_rejected_by_form(self):
        """Pillow content check lives in the form field (the admin uses the same one)."""
        form_class = modelform_factory(ProductImage, fields=["image"])
        fake = SimpleUploadedFile("x.jpg", b"hello, I am not an image", content_type="image/jpeg")
        form = form_class(files={"image": fake})
        assert not form.is_valid()
        assert "image" in form.errors

    def test_real_image_accepted_by_form(self):
        form_class = modelform_factory(ProductImage, fields=["image"])
        upload = SimpleUploadedFile("x.jpg", make_image_bytes(), content_type="image/jpeg")
        assert form_class(files={"image": upload}).is_valid()

    def test_wrong_extension_rejected(self):
        image = ProductImageFactory.build(image=ContentFile(make_image_bytes(), name="x.gif"))
        with pytest.raises(ValidationError):
            image.full_clean(exclude=["product"])


class TestVideos:
    def test_provider_detected_on_save(self):
        video = ProductVideoFactory(url="https://rutube.ru/video/0123456789abcdef0123456789abcdef/")
        assert video.provider == "rutube"
        assert video.embed_url == "https://rutube.ru/play/embed/0123456789abcdef0123456789abcdef"

    def test_provider_redetected_when_url_changes(self):
        video = ProductVideoFactory()
        assert video.provider == "youtube"
        video.url = "https://vk.com/video-1_2"
        video.save()
        assert video.provider == "vk"

    def test_clean_rejects_unsupported_host(self):
        video = ProductVideoFactory.build(url="https://example.com/video.mp4")
        with pytest.raises(ValidationError) as exc:
            video.clean()
        assert "url" in exc.value.message_dict

    def test_save_raises_for_bad_url(self):
        with pytest.raises(VideoUrlError):
            ProductVideoFactory(url="https://example.com/x")

    def test_embed_url_none_for_unrecognised(self):
        video = ProductVideoFactory()
        type(video).objects.filter(pk=video.pk).update(url="https://x.example/")
        video.refresh_from_db()
        assert video.embed_url is None
