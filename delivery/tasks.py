"""Celery entry. Payment (stage 4) calls ``send_order_files`` after the order becomes paid."""

from celery import shared_task

from delivery.watermark import WatermarkError


@shared_task(
    autoretry_for=(OSError, WatermarkError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_order_files(order_id: str) -> None:
    from delivery.services import issue_paid_order

    issue_paid_order(order_id)
