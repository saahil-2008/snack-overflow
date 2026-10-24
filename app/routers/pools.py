# app/routers/pools.py — Transport pools, matching, reservations, dispatch, telemetry, arrival
# (Sections 4.2, 4.3.6, 4.3.7)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user, require_roles
from app.core.errors import ApiError
from app.db.models import (
    CropProfileRow, HarvestBatchRow, PoolMemberRow, TelemetryReadingRow,
    TransportPoolRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, BatchRulUpdate, CancelReservationResult, CreatePoolRequest,
    CreateReservationRequest, Paginated, PoolMatch, PoolMatchRequest,
    PoolMatchResult, PoolMember, PoolRejection, PoolStatus, RouteTier,
    TelemetryIngestRequest, TelemetryIngestResult, TelemetryReading,
    TransportPool, TransportPoolDetail, EthyleneClass,
)
from app.services.decay import consumed_hours, q10_decay_factor
from app.services.grading import required_route_tier, TIER_RANK
from app.services.pagination import paginate
from app.services.pooling import check_compatibility, compute_match_score, haversine

router = APIRouter(prefix="/api/v1/pools", tags=["pools"])


# ─── DTO helpers ───

def _pool_computed(pool_row: TransportPoolRow, db: Session) -> dict:
    """Compute the dynamic fields for a pool DTO."""
    carrier = db.query(UserRow).filter(UserRow.id == pool_row.carrier_id).first()
    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_row.id).all()
    booked = sum(m.kg_booked for m in members)

    ethylene_set: set[str] = set()
    for m in members:
        b = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
        if b:
            c = db.query(CropProfileRow).filter(CropProfileRow.id == b.crop_profile_id).first()
            if c:
                ethylene_set.add(c.ethylene_class)
    eth_order = ["EMITTER", "SENSITIVE", "NEUTRAL"]
    ethylene_classes = [e for e in eth_order if e in ethylene_set]

    return {
        "carrier_name": carrier.name if carrier else "Unknown",
        "booked_capacity_kg": booked,
        "member_count": len(members),
        "ethylene_classes": ethylene_classes,
    }


def _pool_dto(pool_row: TransportPoolRow, db: Session) -> TransportPool:
    c = _pool_computed(pool_row, db)
    return TransportPool(
        id=pool_row.id,
        carrier_id=pool_row.carrier_id,
        carrier_name=c["carrier_name"],
        route_tier=pool_row.route_tier,
        status=pool_row.status,
        origin_label=pool_row.origin_label,
        origin_latitude=round(pool_row.origin_latitude, 6),
        origin_longitude=round(pool_row.origin_longitude, 6),
        destination_name=pool_row.destination_name,
        destination_latitude=round(pool_row.destination_latitude, 6),
        destination_longitude=round(pool_row.destination_longitude, 6),
        max_capacity_kg=round(pool_row.max_capacity_kg, 2),
        booked_capacity_kg=round(c["booked_capacity_kg"], 2),
        member_count=c["member_count"],
        cohort_target_rul_hours=round(pool_row.cohort_target_rul_hours, 1) if pool_row.cohort_target_rul_hours is not None else None,
        ethylene_classes=c["ethylene_classes"],
        pickup_window_start=pool_row.pickup_window_start,
        pickup_window_end=pool_row.pickup_window_end,
        dispatched_at=pool_row.dispatched_at,
        arrived_at=pool_row.arrived_at,
        created_at=pool_row.created_at,
    )


def _member_dto(m: PoolMemberRow, db: Session) -> PoolMember:
    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
    farmer = db.query(UserRow).filter(UserRow.id == batch.farmer_id).first() if batch else None
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first() if batch else None
    return PoolMember(
        id=m.id,
        pool_id=m.pool_id,
        batch_id=m.batch_id,
        farmer_id=batch.farmer_id if batch else uuid4(),
        farmer_name=farmer.name if farmer else "Unknown",
        crop_name=crop.crop_name if crop else "UNKNOWN",
        ethylene_class=crop.ethylene_class if crop else "NEUTRAL",
        kg_booked=round(m.kg_booked, 2),
        current_rul_hours=round(batch.current_rul_hours, 1) if batch and batch.current_rul_hours is not None else None,
        reserved_at=m.reserved_at,
    )


def _pool_detail_dto(pool_row: TransportPoolRow, db: Session) -> TransportPoolDetail:
    pool = _pool_dto(pool_row, db)
    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_row.id).all()
    member_dtos = [_member_dto(m, db) for m in members]
    return TransportPoolDetail(**pool.model_dump(by_alias=False), members=member_dtos)


# ─── Routes ───

@router.post("", status_code=201, response_model=ApiSuccess[TransportPoolDetail])
def create_pool(
    body: CreatePoolRequest,
    user: CurrentUser = Depends(require_roles("LOGISTICS")),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    pool_id = uuid4()
    row = TransportPoolRow(
        id=pool_id,
        carrier_id=user.user_id,
        route_tier=body.route_tier,
        status="OPEN",
        origin_label=body.origin_label,
        origin_latitude=body.origin_latitude,
        origin_longitude=body.origin_longitude,
        destination_name=body.destination_name,
        destination_latitude=body.destination_latitude,
        destination_longitude=body.destination_longitude,
        max_capacity_kg=body.max_capacity_kg,
        cohort_target_rul_hours=None,
        pickup_window_start=body.pickup_window_start,
        pickup_window_end=body.pickup_window_end,
        dispatched_at=None,
        arrived_at=None,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_pool_detail_dto(row, db))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[TransportPool]])
def list_pools(
    status: PoolStatus | None = Query(default=None),
    route_tier: RouteTier | None = Query(default=None, alias="routeTier"),
    mine: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TransportPoolRow)

    # Visibility scoping (Section 4.3.1)
    if user.role == "LOGISTICS" and mine:
        q = q.filter(TransportPoolRow.carrier_id == user.user_id)
    elif user.role in ("FARMER", "BUYER") and not status:
        q = q.filter(TransportPoolRow.status == "OPEN")
    # ADMIN and LOGISTICS (without mine) see all

    if status:
        q = q.filter(TransportPoolRow.status == status)
    if route_tier:
        q = q.filter(TransportPoolRow.route_tier == route_tier)

    items, next_cursor = paginate(q, TransportPoolRow, limit, cursor)
    dtos = [_pool_dto(r, db) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{pool_id}", status_code=200, response_model=ApiSuccess[TransportPoolDetail])
def get_pool(
    pool_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})
    return ApiSuccess(data=_pool_detail_dto(row, db))


@router.post("/match", status_code=200, response_model=ApiSuccess[PoolMatchResult])
def match_pools(
    body: PoolMatchRequest,
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == body.batch_id).first()
    if not batch:
        raise ApiError(404, "NOT_FOUND", "Batch not found",
                       {"resource": "batch", "id": str(body.batch_id)})
    if batch.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This batch belongs to another farmer",
                       {"resource": "batch", "id": str(body.batch_id)})
    if batch.status != "GRADED":
        raise ApiError(409, "BATCH_STATE_INVALID",
                       f"Batch must be GRADED for pool matching, got {batch.status}",
                       {"currentStatus": batch.status, "requiredStatuses": ["GRADED"]})

    batch_rul = batch.current_rul_hours or 0.0
    batch_tier = required_route_tier(batch_rul)
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()

    now = datetime.now(timezone.utc)
    all_pools = db.query(TransportPoolRow).filter(TransportPoolRow.status == "OPEN").all()

    matches = []
    rejected = []

    for pool_row in all_pools:
        c = _pool_computed(pool_row, db)
        reasons = check_compatibility(
            batch_pickup_lat=batch.pickup_latitude,
            batch_pickup_lng=batch.pickup_longitude,
            batch_ethylene=crop.ethylene_class if crop else "NEUTRAL",
            batch_rul_hours=batch_rul,
            batch_weight_kg=batch.weight_kg,
            pool_status=pool_row.status,
            pool_origin_lat=pool_row.origin_latitude,
            pool_origin_lng=pool_row.origin_longitude,
            pool_pickup_window_end=pool_row.pickup_window_end,
            pool_ethylene_classes=c["ethylene_classes"],
            pool_cohort_target_rul_hours=pool_row.cohort_target_rul_hours,
            pool_route_tier=pool_row.route_tier,
            pool_booked_capacity_kg=c["booked_capacity_kg"],
            pool_max_capacity_kg=pool_row.max_capacity_kg,
            now=now,
        )

        if reasons:
            rejected.append(PoolRejection(pool_id=pool_row.id, reasons=reasons))
        else:
            dist = haversine(batch.pickup_latitude, batch.pickup_longitude,
                             pool_row.origin_latitude, pool_row.origin_longitude)
            rul_delta = (batch_rul - pool_row.cohort_target_rul_hours) if pool_row.cohort_target_rul_hours is not None else None
            remaining = pool_row.max_capacity_kg - c["booked_capacity_kg"]
            score = compute_match_score(dist, rul_delta)
            matches.append(PoolMatch(
                pool=_pool_dto(pool_row, db),
                distance_km=round(dist, 1),
                rul_delta_hours=round(rul_delta, 1) if rul_delta is not None else None,
                remaining_capacity_kg=round(remaining, 2),
                score=round(score, 3),
            ))

    # Sort matches: score desc, distance asc
    matches.sort(key=lambda m: (-m.score, m.distance_km))
    matches = matches[:10]
    rejected = rejected[:50]

    return ApiSuccess(data=PoolMatchResult(
        batch_id=body.batch_id,
        batch_rul_hours=round(batch_rul, 1),
        required_route_tier=batch_tier,
        matches=matches,
        rejected=rejected,
    ))


@router.post("/{pool_id}/reservations", status_code=201, response_model=ApiSuccess[PoolMember])
def create_reservation(
    pool_id: UUID,
    body: CreateReservationRequest,
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})

    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == body.batch_id).first()
    if not batch:
        raise ApiError(404, "NOT_FOUND", "Batch not found",
                       {"resource": "batch", "id": str(body.batch_id)})
    if batch.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This batch belongs to another farmer",
                       {"resource": "batch", "id": str(body.batch_id)})
    if batch.status != "GRADED":
        raise ApiError(409, "BATCH_STATE_INVALID",
                       f"Batch must be GRADED for reservation, got {batch.status}",
                       {"currentStatus": batch.status, "requiredStatuses": ["GRADED"]})

    # Re-run compatibility
    now = datetime.now(timezone.utc)
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()
    c = _pool_computed(pool_row, db)
    reasons = check_compatibility(
        batch_pickup_lat=batch.pickup_latitude,
        batch_pickup_lng=batch.pickup_longitude,
        batch_ethylene=crop.ethylene_class if crop else "NEUTRAL",
        batch_rul_hours=batch.current_rul_hours or 0.0,
        batch_weight_kg=batch.weight_kg,
        pool_status=pool_row.status,
        pool_origin_lat=pool_row.origin_latitude,
        pool_origin_lng=pool_row.origin_longitude,
        pool_pickup_window_end=pool_row.pickup_window_end,
        pool_ethylene_classes=c["ethylene_classes"],
        pool_cohort_target_rul_hours=pool_row.cohort_target_rul_hours,
        pool_route_tier=pool_row.route_tier,
        pool_booked_capacity_kg=c["booked_capacity_kg"],
        pool_max_capacity_kg=pool_row.max_capacity_kg,
        now=now,
    )
    if reasons:
        raise ApiError(409, "POOL_INCOMPATIBLE",
                       "Batch is not compatible with this pool",
                       {"reasons": reasons})

    member_id = uuid4()
    member_row = PoolMemberRow(
        id=member_id,
        pool_id=pool_id,
        batch_id=body.batch_id,
        kg_booked=batch.weight_kg,
        reserved_at=now,
    )
    db.add(member_row)

    # First member sets cohort target
    if c["member_count"] == 0:
        pool_row.cohort_target_rul_hours = batch.current_rul_hours

    batch.status = "POOLED"
    db.commit()
    db.refresh(member_row)

    return ApiSuccess(data=_member_dto(member_row, db))


@router.delete("/{pool_id}/reservations/{batch_id}", status_code=200,
               response_model=ApiSuccess[CancelReservationResult])
def cancel_reservation(
    pool_id: UUID,
    batch_id: UUID,
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.status != "OPEN":
        raise ApiError(409, "POOL_STATE_INVALID",
                       f"Pool must be OPEN to cancel reservation, got {pool_row.status}",
                       {"currentStatus": pool_row.status})

    member = db.query(PoolMemberRow).filter(
        PoolMemberRow.pool_id == pool_id,
        PoolMemberRow.batch_id == batch_id,
    ).first()
    if not member:
        raise ApiError(404, "NOT_FOUND", "Reservation not found",
                       {"resource": "poolMember", "poolId": str(pool_id), "batchId": str(batch_id)})

    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == batch_id).first()
    if not batch or batch.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This batch belongs to another farmer",
                       {"resource": "batch", "id": str(batch_id)})

    db.delete(member)
    batch.status = "GRADED"

    # If pool is now empty, clear cohort target
    remaining = db.query(PoolMemberRow).filter(
        PoolMemberRow.pool_id == pool_id,
        PoolMemberRow.id != member.id,
    ).count()
    if remaining == 0:
        pool_row.cohort_target_rul_hours = None

    db.commit()

    return ApiSuccess(data=CancelReservationResult(
        pool_id=pool_id,
        batch_id=batch_id,
        batch_status="GRADED",
    ))


@router.post("/{pool_id}/dispatch", status_code=200, response_model=ApiSuccess[TransportPoolDetail])
def dispatch_pool(
    pool_id: UUID,
    user: CurrentUser = Depends(require_roles("LOGISTICS")),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.carrier_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This pool is not yours",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.status != "OPEN":
        raise ApiError(409, "POOL_STATE_INVALID",
                       f"Pool must be OPEN to dispatch, got {pool_row.status}",
                       {"currentStatus": pool_row.status, "reason": pool_row.status})

    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_id).all()
    if len(members) == 0:
        raise ApiError(409, "POOL_STATE_INVALID",
                       "Pool has no members",
                       {"currentStatus": pool_row.status, "reason": "Pool has no members"})

    now = datetime.now(timezone.utc)

    # Age each member batch at reference temperature
    for m in members:
        batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
        if not batch:
            continue
        if batch.current_rul_hours is not None and batch.rul_updated_at is not None:
            elapsed = (now - batch.rul_updated_at).total_seconds() / 3600.0
            batch.current_rul_hours = max(0, batch.current_rul_hours - elapsed)
        batch.rul_at_dispatch_hours = batch.current_rul_hours
        batch.rul_updated_at = now
        batch.status = "IN_TRANSIT"

    pool_row.dispatched_at = now
    pool_row.status = "IN_TRANSIT"

    db.commit()
    db.refresh(pool_row)
    return ApiSuccess(data=_pool_detail_dto(pool_row, db))


@router.post("/{pool_id}/telemetry", status_code=201,
             response_model=ApiSuccess[TelemetryIngestResult])
def ingest_telemetry(
    pool_id: UUID,
    body: TelemetryIngestRequest,
    user: CurrentUser = Depends(require_roles("LOGISTICS")),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.carrier_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This pool is not yours",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.status != "IN_TRANSIT":
        raise ApiError(409, "POOL_STATE_INVALID",
                       f"Pool must be IN_TRANSIT for telemetry, got {pool_row.status}",
                       {"currentStatus": pool_row.status})

    now = datetime.now(timezone.utc)
    recorded_at = body.recorded_at if body.recorded_at else now

    # Get previous reading's recorded_at or dispatched_at
    last_reading = db.query(TelemetryReadingRow).filter(
        TelemetryReadingRow.pool_id == pool_id,
    ).order_by(TelemetryReadingRow.recorded_at.desc()).first()

    previous_at = last_reading.recorded_at if last_reading else pool_row.dispatched_at

    if recorded_at <= previous_at:
        raise ApiError(409, "TELEMETRY_OUT_OF_ORDER",
                       "recordedAt must be after the previous reading",
                       {"previousAt": previous_at.isoformat(), "recordedAt": recorded_at.isoformat()})

    interval_hours = (recorded_at - previous_at).total_seconds() / 3600.0

    reading_id = uuid4()
    reading_row = TelemetryReadingRow(
        id=reading_id,
        pool_id=pool_id,
        temp_c=body.temp_c,
        latitude=body.latitude,
        longitude=body.longitude,
        recorded_at=recorded_at,
        created_at=now,
    )
    db.add(reading_row)

    # Update each member batch's RUL via Q10 decay
    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_id).all()
    batch_updates = []
    min_rul = float("inf")

    for m in members:
        batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
        if not batch or batch.current_rul_hours is None:
            continue
        crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()
        if not crop:
            continue

        prev_rul = batch.current_rul_hours
        factor = q10_decay_factor(crop.q10, body.temp_c, crop.reference_temp_c)
        consumed = consumed_hours(interval_hours, factor)
        new_rul = max(0.0, prev_rul - consumed)

        batch.current_rul_hours = new_rul
        batch.rul_updated_at = recorded_at

        batch_updates.append(BatchRulUpdate(
            batch_id=batch.id,
            previous_rul_hours=round(prev_rul, 1),
            decay_factor=round(factor, 3),
            consumed_hours=round(consumed, 1),
            current_rul_hours=round(new_rul, 1),
        ))

        if new_rul < min_rul:
            min_rul = new_rul

    # Reroute suggestion
    reroute_suggested = False
    suggested_tier = None
    if min_rul < float("inf"):
        suggested = required_route_tier(min_rul)
        if TIER_RANK.get(suggested, 2) < TIER_RANK.get(pool_row.route_tier, 2):
            reroute_suggested = True
            suggested_tier = suggested

    db.commit()
    db.refresh(reading_row)

    return ApiSuccess(data=TelemetryIngestResult(
        reading=TelemetryReading.model_validate(reading_row, from_attributes=True),
        interval_hours=round(interval_hours, 1),
        batch_updates=batch_updates,
        reroute_suggested=reroute_suggested,
        suggested_route_tier=suggested_tier,
    ))


@router.get("/{pool_id}/telemetry", status_code=200,
            response_model=ApiSuccess[Paginated[TelemetryReading]])
def list_telemetry(
    pool_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})

    q = db.query(TelemetryReadingRow).filter(TelemetryReadingRow.pool_id == pool_id)
    items, next_cursor = paginate(q, TelemetryReadingRow, limit, cursor,
                                  sort_field="recorded_at", ascending=True)
    dtos = [TelemetryReading.model_validate(r, from_attributes=True) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.post("/{pool_id}/arrive", status_code=200, response_model=ApiSuccess[TransportPoolDetail])
def arrive_pool(
    pool_id: UUID,
    user: CurrentUser = Depends(require_roles("LOGISTICS")),
    db: Session = Depends(get_db),
):
    pool_row = db.query(TransportPoolRow).filter(TransportPoolRow.id == pool_id).first()
    if not pool_row:
        raise ApiError(404, "NOT_FOUND", "Pool not found",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.carrier_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This pool is not yours",
                       {"resource": "pool", "id": str(pool_id)})
    if pool_row.status != "IN_TRANSIT":
        raise ApiError(409, "POOL_STATE_INVALID",
                       f"Pool must be IN_TRANSIT to arrive, got {pool_row.status}",
                       {"currentStatus": pool_row.status})

    now = datetime.now(timezone.utc)

    # Close the final interval
    last_reading = db.query(TelemetryReadingRow).filter(
        TelemetryReadingRow.pool_id == pool_id,
    ).order_by(TelemetryReadingRow.recorded_at.desc()).first()

    arrived_at = max(now, last_reading.recorded_at) if last_reading else now
    previous_at = last_reading.recorded_at if last_reading else pool_row.dispatched_at
    final_temp = last_reading.temp_c if last_reading else None

    if previous_at and arrived_at > previous_at:
        interval_hours = (arrived_at - previous_at).total_seconds() / 3600.0
        members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_id).all()
        for m in members:
            batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
            if not batch or batch.current_rul_hours is None:
                continue
            crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()
            if not crop:
                continue

            temp = final_temp if final_temp is not None else crop.reference_temp_c
            factor = q10_decay_factor(crop.q10, temp, crop.reference_temp_c)
            consumed = consumed_hours(interval_hours, factor)
            batch.current_rul_hours = max(0.0, batch.current_rul_hours - consumed)
            batch.rul_updated_at = arrived_at
            batch.status = "ARRIVED"

    # Set any remaining member batches to ARRIVED
    members = db.query(PoolMemberRow).filter(PoolMemberRow.pool_id == pool_id).all()
    for m in members:
        batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == m.batch_id).first()
        if batch and batch.status != "ARRIVED":
            batch.status = "ARRIVED"
            batch.rul_updated_at = arrived_at

    pool_row.arrived_at = arrived_at
    pool_row.status = "ARRIVED"

    db.commit()
    db.refresh(pool_row)
    return ApiSuccess(data=_pool_detail_dto(pool_row, db))
