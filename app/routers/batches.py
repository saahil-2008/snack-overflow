# app/routers/batches.py — batch CRUD (Section 4.2, 4.3.1)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user
from app.core.config import FRONTEND_BASE_URL
from app.core.errors import ApiError
from app.db.models import (
    CropProfileRow, HarvestAdvisoryRow, HarvestBatchRow, PoolMemberRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, BatchStatus, CreateBatchRequest, HarvestBatch, Paginated,
)
from app.services.pagination import paginate

router = APIRouter(prefix="/api/v1/batches", tags=["batches"])


def batch_dto(row: HarvestBatchRow, db: Session) -> HarvestBatch:
    farmer = db.query(UserRow).filter(UserRow.id == row.farmer_id).first()
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == row.crop_profile_id).first()

    # poolId: check pool_members for this batch
    member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == row.id).first()
    pool_id = member.pool_id if member else None

    return HarvestBatch(
        id=row.id,
        farmer_id=row.farmer_id,
        farmer_name=farmer.name if farmer else "Unknown",
        crop_profile_id=row.crop_profile_id,
        crop_name=crop.crop_name if crop else "UNKNOWN",
        ethylene_class=crop.ethylene_class if crop else "NEUTRAL",
        harvest_advisory_id=row.harvest_advisory_id,
        weight_kg=round(row.weight_kg, 2),
        avg_fruit_mass_g=round(row.avg_fruit_mass_g, 2),
        harvested_at=row.harvested_at,
        pickup_latitude=round(row.pickup_latitude, 6),
        pickup_longitude=round(row.pickup_longitude, 6),
        status=row.status,
        quality_grade=row.quality_grade,
        internal_defect_flag=row.internal_defect_flag,
        stiffness_index=round(row.stiffness_index) if row.stiffness_index is not None else None,
        loading_stiffness_index=round(row.loading_stiffness_index) if row.loading_stiffness_index is not None else None,
        initial_rul_hours=round(row.initial_rul_hours, 1) if row.initial_rul_hours is not None else None,
        current_rul_hours=round(row.current_rul_hours, 1) if row.current_rul_hours is not None else None,
        rul_updated_at=row.rul_updated_at,
        rul_at_dispatch_hours=round(row.rul_at_dispatch_hours, 1) if row.rul_at_dispatch_hours is not None else None,
        pool_id=pool_id,
        qr_code_value=f"{FRONTEND_BASE_URL}/passport/{row.id}",
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ApiSuccess[HarvestBatch])
def create_batch(
    body: CreateBatchRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role != "FARMER":
        raise ApiError(403, "FORBIDDEN_ROLE", "Only farmers can create batches",
                       {"requiredRoles": ["FARMER"], "yourRole": user.role})

    # Validate crop profile
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == body.crop_profile_id).first()
    if not crop:
        raise ApiError(404, "NOT_FOUND", "Crop profile not found",
                       {"resource": "cropProfile", "id": str(body.crop_profile_id)})

    # Validate advisory if provided
    if body.harvest_advisory_id:
        adv = db.query(HarvestAdvisoryRow).filter(HarvestAdvisoryRow.id == body.harvest_advisory_id).first()
        if not adv:
            raise ApiError(404, "NOT_FOUND", "Advisory not found",
                           {"resource": "harvestAdvisory", "id": str(body.harvest_advisory_id)})

    now = datetime.now(timezone.utc)
    batch_id = uuid4()
    row = HarvestBatchRow(
        id=batch_id,
        farmer_id=user.user_id,
        crop_profile_id=body.crop_profile_id,
        harvest_advisory_id=body.harvest_advisory_id,
        weight_kg=body.weight_kg,
        avg_fruit_mass_g=body.avg_fruit_mass_g,
        harvested_at=body.harvested_at,
        pickup_latitude=body.pickup_latitude,
        pickup_longitude=body.pickup_longitude,
        status="PENDING_ASSAY",
        quality_grade=None,
        internal_defect_flag=False,
        stiffness_index=None,
        loading_stiffness_index=None,
        initial_rul_hours=None,
        current_rul_hours=None,
        rul_updated_at=None,
        rul_at_dispatch_hours=None,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ApiSuccess(data=batch_dto(row, db))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[HarvestBatch]])
def list_batches(
    status: BatchStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(HarvestBatchRow)

    # Scope by role (Section 4.3.1)
    if user.role == "FARMER":
        q = q.filter(HarvestBatchRow.farmer_id == user.user_id)
    elif user.role == "LOGISTICS":
        # Batches in pools they carry
        from app.db.models import TransportPoolRow
        pool_ids = [p.id for p in db.query(TransportPoolRow).filter(TransportPoolRow.carrier_id == user.user_id).all()]
        if pool_ids:
            batch_ids = [m.batch_id for m in db.query(PoolMemberRow).filter(PoolMemberRow.pool_id.in_(pool_ids)).all()]
            q = q.filter(HarvestBatchRow.id.in_(batch_ids))
        else:
            q = q.filter(False)  # no results
    elif user.role == "BUYER":
        # Batches in their orders
        from app.db.models import BuyerOrderRow
        batch_ids = [o.batch_id for o in db.query(BuyerOrderRow).filter(BuyerOrderRow.buyer_id == user.user_id).all()]
        q = q.filter(HarvestBatchRow.id.in_(batch_ids))
    # ADMIN sees all

    if status:
        q = q.filter(HarvestBatchRow.status == status)

    items, next_cursor = paginate(q, HarvestBatchRow, limit, cursor)
    dtos = [batch_dto(r, db) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{batch_id}", status_code=200, response_model=ApiSuccess[HarvestBatch])
def get_batch(
    batch_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == batch_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Batch not found",
                       {"resource": "batch", "id": str(batch_id)})

    # Ownership check (Section 4.3.1)
    if user.role == "FARMER" and row.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This batch belongs to another farmer",
                       {"resource": "batch", "id": str(batch_id)})
    elif user.role == "LOGISTICS":
        from app.db.models import TransportPoolRow
        member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == batch_id).first()
        if not member:
            raise ApiError(403, "NOT_OWNER", "This batch is not in your pool",
                           {"resource": "batch", "id": str(batch_id)})
        pool = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()
        if not pool or pool.carrier_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This batch is not in your pool",
                           {"resource": "batch", "id": str(batch_id)})
    elif user.role == "BUYER":
        from app.db.models import BuyerOrderRow
        has_order = db.query(BuyerOrderRow).filter(
            BuyerOrderRow.batch_id == batch_id,
            BuyerOrderRow.buyer_id == user.user_id
        ).first()
        if not has_order:
            raise ApiError(403, "NOT_OWNER", "You have no order on this batch",
                           {"resource": "batch", "id": str(batch_id)})
    # ADMIN: no restriction

    return ApiSuccess(data=batch_dto(row, db))
