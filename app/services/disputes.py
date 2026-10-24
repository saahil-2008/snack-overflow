# app/services/disputes.py — Dispute attribution logic (Section 4.3.10)
from datetime import datetime

from app.services.grading import rul_from_curve
from app.services.decay import shelf_rul


def build_dispute(order, batch, crop, scans, pool, now: datetime) -> dict:
    """Build dispute report data including checkpoints, segments and attribution.

    Args:
        order: BuyerOrderRow
        batch: HarvestBatchRow
        crop: CropProfileRow (with rul_curve as list of dicts with camelCase keys)
        scans: list of AcousticScanRow for this batch
        pool: TransportPoolRow or None
        now: current UTC datetime

    Returns dict with all dispute fields.
    """
    # Separate scans by stage
    farm_gate_scans = [s for s in scans if s.stage == "FARM_GATE"]
    loading_scans = [s for s in scans if s.stage == "LOADING"]

    # --- Checkpoint: Farm gate ---
    farm_gate_at = max((s.recorded_at for s in farm_gate_scans), default=batch.created_at)
    rul_farm_gate_hours = batch.initial_rul_hours or 0.0

    # --- Checkpoint: Loading ---
    rul_curve = crop.rul_curve  # stored as camelCase dicts
    if loading_scans:
        loading_at = max(s.recorded_at for s in loading_scans)
        loading_source = "SCAN"
        rul_loading_hours = rul_from_curve(batch.loading_stiffness_index, rul_curve)
    else:
        loading_at = pool.dispatched_at if pool else farm_gate_at
        loading_source = "MODEL"
        rul_loading_hours = batch.rul_at_dispatch_hours if batch.rul_at_dispatch_hours is not None else rul_farm_gate_hours

    # --- Checkpoint: Intake ---
    intake_at = order.intake_verified_at
    rul_intake_hours = order.rul_at_intake_hours or 0.0

    # --- Checkpoint: Shelf (assessed now) ---
    assessed_at = now
    rul_shelf_hours = shelf_rul(
        rul_at_intake_hours=order.rul_at_intake_hours or 0.0,
        intake_verified_at=order.intake_verified_at,
        now=now,
        storage_temp_c=order.storage_temp_c or crop.reference_temp_c,
        q10=crop.q10,
        reference_temp_c=crop.reference_temp_c,
    )

    # --- Segments ---
    def make_segment(party: str, start_at, end_at, start_rul: float, end_rul: float) -> dict:
        elapsed_hours = max(0.0, (end_at - start_at).total_seconds() / 3600.0)
        actual_loss_hours = start_rul - end_rul
        expected_loss_hours = elapsed_hours  # normal ageing at reference temperature
        excess_loss_hours = actual_loss_hours - expected_loss_hours
        return {
            "party": party,
            "start_at": start_at,
            "end_at": end_at,
            "elapsed_hours": elapsed_hours,
            "actual_loss_hours": actual_loss_hours,
            "expected_loss_hours": expected_loss_hours,
            "excess_loss_hours": excess_loss_hours,
        }

    segments = [
        make_segment("FARM", farm_gate_at, loading_at, rul_farm_gate_hours, rul_loading_hours),
        make_segment("TRANSIT", loading_at, intake_at, rul_loading_hours, rul_intake_hours),
        make_segment("BUYER_STORAGE", intake_at, assessed_at, rul_intake_hours, rul_shelf_hours),
    ]

    # --- Attribution ---
    max_excess = max(s["excess_loss_hours"] for s in segments)
    if max_excess > crop.dispute_tolerance_hours:
        responsible = max(segments, key=lambda s: s["excess_loss_hours"])["party"]
    else:
        responsible = "NONE"

    return {
        "rul_farm_gate_hours": rul_farm_gate_hours,
        "rul_loading_hours": rul_loading_hours,
        "rul_intake_hours": rul_intake_hours,
        "rul_shelf_hours": rul_shelf_hours,
        "farm_gate_at": farm_gate_at,
        "loading_at": loading_at,
        "intake_at": intake_at,
        "assessed_at": assessed_at,
        "loading_checkpoint_source": loading_source,
        "segments": segments,
        "responsible_party": responsible,
    }
