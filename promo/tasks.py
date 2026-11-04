from celery import shared_task


@shared_task
def tick_preorders() -> dict:
    from promo.services import tick_preorders as run

    return run()
