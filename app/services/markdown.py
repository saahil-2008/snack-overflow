# app/services/markdown.py — Flash-markdown trigger logic (Section 4.3.9)
import logging

from app.services.decay import shelf_rul

log = logging.getLogger("farmpool")


def compute_markdown_check(
    order,
    batch,
    crop,
    simulate_hours_ahead: float | None,
    now,
) -> dict:
    """Compute markdown check result.

    Returns dict with keys: shelf_rul_hours, threshold_hours, markdown_active,
    newly_triggered, webhook_payload, order (updated).
    """
    from datetime import timedelta

    t = now + timedelta(hours=simulate_hours_ahead or 0)

    shelf_rul_hours = shelf_rul(
        rul_at_intake_hours=order.rul_at_intake_hours,
        intake_verified_at=order.intake_verified_at,
        now=t,
        storage_temp_c=order.storage_temp_c,
        q10=crop.q10,
        reference_temp_c=crop.reference_temp_c,
    )

    threshold_hours = crop.markdown_threshold_hours
    newly_triggered = False
    webhook_payload = None

    if shelf_rul_hours < threshold_hours and order.markdown_triggered_at is None:
        newly_triggered = True
        order.markdown_pct = crop.default_markdown_pct
        order.markdown_triggered_at = now

        webhook_payload = {
            "event": "FLASH_MARKDOWN",
            "order_id": order.id,
            "batch_id": order.batch_id,
            "crop_name": crop.crop_name,
            "markdown_pct": crop.default_markdown_pct,
            "shelf_rul_hours": shelf_rul_hours,
            "triggered_at": now,
        }

        log.info("Markdown webhook payload: %s", webhook_payload)

    markdown_active = order.markdown_triggered_at is not None

    return {
        "shelf_rul_hours": shelf_rul_hours,
        "threshold_hours": threshold_hours,
        "markdown_active": markdown_active,
        "newly_triggered": newly_triggered,
        "webhook_payload": webhook_payload,
    }
