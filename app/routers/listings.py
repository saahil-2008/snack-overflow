# app/routers/listings.py — Marketplace listings (Section 4.2, 4.3.8)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user, require_roles
from app.core.errors import ApiError
from app.db.models import (
    CropProfileRow, HarvestBatchRow, ListingRow, PoolMemberRow,
    TransportPoolRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, CreateListingRequest, Listing, Paginated, QualityGrade,
)
from app.services.grading import required_route_tier, TIER_TRANSIT_HOURS
from app.services.pagination import paginate

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])


def _listing_dto(row: ListingRow, db: Session) -> Listing:
    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == row.batch_id).first()
    farmer = db.query(UserRow).filter(UserRow.id == row.farmer_id).first()
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first() if batch else None

    # Route tier: pool tier if pooled, else computed from RUL
    member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == row.batch_id).first() if batch else None
    if member:
        pool = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()
        route_tier = pool.route_tier if pool else required_route_tier(batch.current_rul_hours or 0)
    else:
        route_tier = required_route_tier(batch.current_rul_hours or 0) if batch else "STANDARD_WHOLESALE"

    current_rul = batch.current_rul_hours if batch and batch.current_rul_hours is not None else 0.0
    transit_hours = TIER_TRANSIT_HOURS.get(route_tier, 24)
    guaranteed_arrival_rul = max(0.0, current_rul - transit_hours)

    return Listing(
        id=row.id,
        batch_id=row.batch_id,
        farmer_id=row.farmer_id,
        farmer_name=farmer.name if farmer else "Unknown",
        crop_profile_id=batch.crop_profile_id if batch else uuid4(),
        crop_name=crop.crop_name if crop else "UNKNOWN",
        quality_grade=batch.quality_grade if batch else "C",
        internal_defect_flag=batch.internal_defect_flag if batch else False,
        quantity_kg=round(row.quantity_kg, 2),
        available_kg=round(row.available_kg, 2),
        price_per_kg_inr=round(row.price_per_kg_inr, 2),
        current_rul_hours=round(current_rul, 1),
        route_tier=route_tier,
        guaranteed_arrival_rul_hours=round(guaranteed_arrival_rul, 1),
        pickup_latitude=round(batch.pickup_latitude, 6) if batch else 0.0,
        pickup_longitude=round(batch.pickup_longitude, 6) if batch else 0.0,
        status=row.status,
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ApiSuccess[Listing])
def create_listing(
    body: CreateListingRequest,
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
    if batch.status not in ("GRADED", "POOLED", "IN_TRANSIT"):
        raise ApiError(409, "BATCH_STATE_INVALID",
                       f"Batch must be GRADED, POOLED or IN_TRANSIT to list, got {batch.status}",
                       {"currentStatus": batch.status,
                        "requiredStatuses": ["GRADED", "POOLED", "IN_TRANSIT"]})
    if body.quantity_kg > batch.weight_kg:
        raise ApiError(422, "VALIDATION_ERROR", "Request validation failed",
                       {"fields": [{"field": "quantityKg",
                                    "message": f"quantityKg ({body.quantity_kg}) exceeds batch weight ({batch.weight_kg})",
                                    "type": "value_error"}]})

    # At most one ACTIVE listing per batch
    existing = db.query(ListingRow).filter(
        ListingRow.batch_id == body.batch_id,
        ListingRow.status == "ACTIVE",
    ).first()
    if existing:
        raise ApiError(409, "LISTING_UNAVAILABLE",
                       "This batch already has an active listing",
                       {"existingListingId": str(existing.id)})

    now = datetime.now(timezone.utc)
    listing_id = uuid4()
    row = ListingRow(
        id=listing_id,
        batch_id=body.batch_id,
        farmer_id=user.user_id,
        quantity_kg=body.quantity_kg,
        available_kg=body.quantity_kg,
        price_per_kg_inr=body.price_per_kg_inr,
        status="ACTIVE",
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_listing_dto(row, db))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[Listing]])
def list_listings(
    crop_profile_id: UUID | None = Query(default=None, alias="cropProfileId"),
    grade: QualityGrade | None = Query(default=None),
    min_arrival_rul_hours: float | None = Query(default=None, alias="minArrivalRulHours"),
    mine: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ListingRow)

    # Visibility scoping (Section 4.3.1)
    if user.role == "FARMER" and mine:
        q = q.filter(ListingRow.farmer_id == user.user_id)
    elif user.role != "ADMIN":
        # Non-admin users without mine=true see only ACTIVE
        if not mine:
            q = q.filter(ListingRow.status == "ACTIVE")

    items, next_cursor = paginate(q, ListingRow, limit, cursor)

    # Build DTOs and apply post-query filters
    dtos = []
    for row in items:
        dto = _listing_dto(row, db)

        # Apply filters that require computed fields
        if crop_profile_id and dto.crop_profile_id != crop_profile_id:
            continue
        if grade and dto.quality_grade != grade:
            continue
        if min_arrival_rul_hours is not None and dto.guaranteed_arrival_rul_hours < min_arrival_rul_hours:
            continue

        dtos.append(dto)

    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{listing_id}", status_code=200, response_model=ApiSuccess[Listing])
def get_listing(
    listing_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(ListingRow).filter(ListingRow.id == listing_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Listing not found",
                       {"resource": "listing", "id": str(listing_id)})
    return ApiSuccess(data=_listing_dto(row, db))


@router.post("/{listing_id}/withdraw", status_code=200, response_model=ApiSuccess[Listing])
def withdraw_listing(
    listing_id: UUID,
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    row = db.query(ListingRow).filter(ListingRow.id == listing_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Listing not found",
                       {"resource": "listing", "id": str(listing_id)})
    if row.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This listing belongs to another farmer",
                       {"resource": "listing", "id": str(listing_id)})
    if row.status != "ACTIVE":
        raise ApiError(409, "LISTING_UNAVAILABLE",
                       f"Listing must be ACTIVE to withdraw, got {row.status}",
                       {"currentStatus": row.status})

    row.status = "WITHDRAWN"
    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_listing_dto(row, db))
