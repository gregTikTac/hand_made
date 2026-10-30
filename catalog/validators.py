"""Upload validators for the catalog."""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_IMAGE_BYTES = 15 * 1024 * 1024

validate_image_extension = FileExtensionValidator(["jpg", "jpeg", "png", "webp"])
validate_pdf_extension = FileExtensionValidator(["pdf"])


def validate_image_size(file) -> None:
    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError(
            "Файл слишком большой (%(size)s МБ). Максимум — %(max)s МБ.",
            params={
                "size": round(file.size / 1024 / 1024, 1),
                "max": MAX_IMAGE_BYTES // 1024 // 1024,
            },
            code="image_too_large",
        )


def validate_pdf_header(file) -> None:
    """The file must really be a PDF (starts with ``%PDF-``), not just named *.pdf."""
    position = file.tell() if hasattr(file, "tell") else 0
    try:
        file.seek(0)
        header = file.read(5)
    finally:
        file.seek(position)
    if header != b"%PDF-":
        raise ValidationError("Файл не похож на PDF.", code="not_a_pdf")
