"""File delivery: watermark, five downloads, thirty-day link, resend to the same address."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.core import mail
from django.core.files.base import ContentFile
from django.utils import timezone
from pypdf import PdfReader, PdfWriter

from catalog.factories import ProductFactory
from catalog.pricing import get_price
from delivery.models import DownloadLink
from delivery.services import issue_paid_order, resend_order
from orders.services import place_order, transition

pytestmark = pytest.mark.django_db


def real_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def paid_order(product, email="buyer@example.com"):
    product.pdf_file.save("schema.pdf", ContentFile(real_pdf()), save=True)
    order = place_order(
        products=[product],
        seen={product.pk: get_price(product).final},
        email=email,
        marketing=False,
        ip="127.0.0.1",
        user_agent="test",
    )
    transition(order, "pay")
    transition(order, "succeeded")
    return order


def test_paid_order_sends_watermarked_link(client):
    order = paid_order(ProductFactory())
    issue_paid_order(order.pk)
    order.refresh_from_db()
    assert order.status == "fulfilled"
    assert len(mail.outbox) == 1
    assert "http://testserver/d/" in mail.outbox[0].body
    link = DownloadLink.objects.get()
    url = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http://"))
    response = client.get(url.removeprefix("http://testserver"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(BytesIO(b"".join(response.streaming_content))).pages
    )
    assert "buyer@example.com" in text
    assert order.number in text
    link.refresh_from_db()
    assert link.download_count == 1


def test_sixth_download_is_refused(client):
    order = paid_order(ProductFactory())
    issue_paid_order(order.pk)
    url = next(
        line for line in mail.outbox[0].body.splitlines() if line.startswith("http://testserver/d/")
    )
    path = url.removeprefix("http://testserver")
    for _ in range(5):
        assert client.get(path).status_code == 200
    assert client.get(path).status_code == 410


def test_resend_revokes_the_old_link(client):
    order = paid_order(ProductFactory())
    issue_paid_order(order.pk)
    old = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http://"))
    assert resend_order(order.pk) is True
    assert client.get(old.removeprefix("http://testserver")).status_code == 404
    new = next(line for line in mail.outbox[-1].body.splitlines() if line.startswith("http://"))
    assert client.get(new.removeprefix("http://testserver")).status_code == 200


def test_unknown_email_gets_the_same_answer(client):
    response = client.post("/d/resend/", {"email": "nobody@example.com"})
    assert response.status_code == 200
    assert "Если заказ с этой почтой есть" in response.content.decode()
    assert mail.outbox == []


def test_expired_link_is_hidden(client):
    order = paid_order(ProductFactory())
    issue_paid_order(order.pk)
    link = DownloadLink.objects.get()
    link.expires_at = timezone.now() - timedelta(days=1)
    link.save(update_fields=["expires_at"])
    url = next(line for line in mail.outbox[0].body.splitlines() if line.startswith("http://"))
    assert client.get(url.removeprefix("http://testserver")).status_code == 404


def test_order_without_pdf_waits_for_release():
    product = ProductFactory(pdf_file=None, status="draft")
    order = place_order(
        products=[product],
        seen={product.pk: get_price(product).final},
        email="buyer@example.com",
        marketing=False,
        ip=None,
        user_agent="",
    )
    transition(order, "pay")
    transition(order, "succeeded")
    issue_paid_order(order.pk)
    order.refresh_from_db()
    assert order.status == "awaiting_release"
    assert DownloadLink.objects.count() == 0
    assert (
        "Предзаказ" in mail.outbox[0].subject
        or "придёт" in mail.outbox[0].body.lower()
        or "Файл" in mail.outbox[0].body
    )
