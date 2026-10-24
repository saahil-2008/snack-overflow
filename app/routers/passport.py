# app/routers/passport.py — public Bio-Clock QR passport (Section 4.2)
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.db.models import (
    AcousticScanRow, HarvestBatchRow, PoolMemberRow,
    TelemetryReadingRow, TransportPoolRow, UserRow, CropProfileRow,
)
from app.db.session import get_db
from app.routers.batches import batch_dto
from app.schemas import (
    AcousticScan, ApiSuccess, BatchPassport, TelemetryReading, TransportPool, EthyleneClass,
)

router = APIRouter(prefix="/api/v1/passport", tags=["passport"])


def _pool_dto(pool_row, db) -> TransportPool:
    carrier = db.query(UserRow).filter(UserRow.id == pool_row.carrier_id).first()
    from app.db.models import PoolMemberRow, HarvestBatchRow, CropProfileRow
    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_row.id).all()
    booked = sum(m.kg_booked for m in members)
    ethylene_set = set()
    for m in members:
        b = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
        if b:
            c = db.query(CropProfileRow).filter(CropProfileRow.id == b.crop_profile_id).first()
            if c:
                ethylene_set.add(c.ethylene_class)
    # Sort ethylene classes in enum order
    eth_order = ["EMITTER", "SENSITIVE", "NEUTRAL"]
    ethylene_classes = [e for e in eth_order if e in ethylene_set]

    return TransportPool(
        id=pool_row.id,
        carrier_id=pool_row.carrier_id,
        carrier_name=carrier.name if carrier else "Unknown",
        route_tier=pool_row.route_tier,
        status=pool_row.status,
        origin_label=pool_row.origin_label,
        origin_latitude=round(pool_row.origin_latitude, 6),
        origin_longitude=round(pool_row.origin_longitude, 6),
        destination_name=pool_row.destination_name,
        destination_latitude=round(pool_row.destination_latitude, 6),
        destination_longitude=round(pool_row.destination_longitude, 6),
        max_capacity_kg=round(pool_row.max_capacity_kg, 2),
        booked_capacity_kg=round(booked, 2),
        member_count=len(members),
        cohort_target_rul_hours=round(pool_row.cohort_target_rul_hours, 1) if pool_row.cohort_target_rul_hours is not None else None,
        ethylene_classes=ethylene_classes,
        pickup_window_start=pool_row.pickup_window_start,
        pickup_window_end=pool_row.pickup_window_end,
        dispatched_at=pool_row.dispatched_at,
        arrived_at=pool_row.arrived_at,
        created_at=pool_row.created_at,
    )


@router.get("/{batch_id}", status_code=200, response_model=ApiSuccess[BatchPassport])
def get_passport(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    row = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == batch_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Batch not found",
                       {"resource": "batch", "id": str(batch_id)})

    batch = batch_dto(row, db)

    # Scans ascending by recordedAt
    scans = db.query(AcousticScanRow).filter(
        AcousticScanRow.batch_id == batch_id
    ).order_by(AcousticScanRow.recorded_at).all()

    scan_dtos = [AcousticScan.model_validate(s, from_attributes=True) for s in scans]

    # Pool
    member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == batch_id).first()
    pool = None
    telemetry_dtos = []
    if member:
        pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()
        if pool_row:
            pool = _pool_dto(pool_row, db)
            readings = db.query(TelemetryReadingRow).filter(
                TelemetryReadingRow.pool_id == pool_row.id
            ).order_by(TelemetryReadingRow.recorded_at).all()
            telemetry_dtos = [TelemetryReading.model_validate(r, from_attributes=True) for r in readings]

    return ApiSuccess(data=BatchPassport(
        batch=batch,
        scans=scan_dtos,
        pool=pool,
        telemetry=telemetry_dtos,
    ))
