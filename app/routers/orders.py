# app/routers/orders.py — Buyer orders and markdown (Sections 4.2, 4.3.8, 4.3.9)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user, require_roles
from app.core.errors import ApiError
from app.db.models import (
    BuyerOrderRow, CropProfileRow, HarvestBatchRow, ListingRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, BuyerOrder, CreateOrderRequest, MarkdownCheckRequest,
    MarkdownCheckResult, MarkdownWebhookPayload, OrderStatus, Paginated,
)
from app.services.markdown import compute_markdown_check
from app.services.pagination import paginate

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def _order_dto(row: BuyerOrderRow, db: Session) -> BuyerOrder:
    buyer = db.query(UserRow).filter(UserRow.id == row.buyer_id).first()
    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == row.batch_id).first()
    crop = db.query(CropProfileRow).filter(
        CropProfileRow.id == batch.crop_profile_id).first() if batch else None

    return BuyerOrder(
        id=row.id,
        buyer_id=row.buyer_id,
        buyer_name=buyer.name if buyer else "Unknown",
        listing_id=row.listing_id,
        batch_id=row.batch_id,
        crop_name=crop.crop_name if crop else "UNKNOWN",
        quantity_kg=round(row.quantity_kg, 2),
        price_per_kg_inr=round(row.price_per_kg_inr, 2),
        total_price_inr=round(row.total_price_inr, 2),
        guaranteed_arrival_rul_hours=round(row.guaranteed_arrival_rul_hours, 1),
        status=row.status,
        intake_scan_id=row.intake_scan_id,
        intake_result=row.intake_result,
        intake_stiffness_drop_pct=round(row.intake_stiffness_drop_pct, 1) if row.intake_stiffness_drop_pct is not None else None,
        rul_at_intake_hours=round(row.rul_at_intake_hours, 1) if row.rul_at_intake_hours is not None else None,
        storage_temp_c=round(row.storage_temp_c, 1) if row.storage_temp_c is not None else None,
        intake_verified_at=row.intake_verified_at,
        markdown_pct=round(row.markdown_pct, 1),
        markdown_triggered_at=row.markdown_triggered_at,
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ApiSuccess[BuyerOrder])
def create_order(
    body: CreateOrderRequest,
    user: CurrentUser = Depends(require_roles("BUYER")),
    db: Session = Depends(get_db),
):
    listing = db.query(ListingRow).filter(ListingRow.id == body.listing_id).first()
    if not listing:
        raise ApiError(404, "NOT_FOUND", "Listing not found",
                       {"resource": "listing", "id": str(body.listing_id)})
    if listing.status != "ACTIVE":
        raise ApiError(409, "LISTING_UNAVAILABLE",
                       f"Listing must be ACTIVE, got {listing.status}",
                       {"currentStatus": listing.status})
    if body.quantity_kg > listing.available_kg:
        raise ApiError(409, "LISTING_UNAVAILABLE",
                       f"Requested {body.quantity_kg} kg but only {listing.available_kg} kg available",
                       {"requestedKg": body.quantity_kg, "availableKg": listing.available_kg})

    # Snapshot price and compute guaranteed arrival RUL
    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == listing.batch_id).first()
    crop = db.query(CropProfileRow).filter(
        CropProfileRow.id == batch.crop_profile_id).first() if batch else None

    from app.db.models import PoolMemberRow, TransportPoolRow
    from app.services.grading import required_route_tier, TIER_TRANSIT_HOURS

    member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == listing.batch_id).first() if batch else None
    if member:
        pool = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()
        route_tier = pool.route_tier if pool else required_route_tier(batch.current_rul_hours or 0)
    else:
        route_tier = required_route_tier(batch.current_rul_hours or 0) if batch else "STANDARD_WHOLESALE"

    current_rul = batch.current_rul_hours if batch and batch.current_rul_hours is not None else 0.0
    transit_hours = TIER_TRANSIT_HOURS.get(route_tier, 24)
    guaranteed_arrival_rul = max(0.0, current_rul - transit_hours)

    now = datetime.now(timezone.utc)
    order_id = uuid4()
    total_price = body.quantity_kg * listing.price_per_kg_inr

    order_row = BuyerOrderRow(
        id=order_id,
        buyer_id=user.user_id,
        listing_id=body.listing_id,
        batch_id=listing.batch_id,
        quantity_kg=body.quantity_kg,
        price_per_kg_inr=listing.price_per_kg_inr,
        total_price_inr=total_price,
        guaranteed_arrival_rul_hours=guaranteed_arrival_rul,
        status="PLACED",
        intake_scan_id=None,
        intake_result=None,
        intake_stiffness_drop_pct=None,
        rul_at_intake_hours=None,
        storage_temp_c=None,
        intake_verified_at=None,
        markdown_pct=0,
        markdown_triggered_at=None,
        created_at=now,
    )
    db.add(order_row)

    # Decrease available_kg; if 0 → SOLD_OUT
    listing.available_kg -= body.quantity_kg
    if listing.available_kg <= 0:
        listing.available_kg = 0
        listing.status = "SOLD_OUT"

    db.commit()
    db.refresh(order_row)
    return ApiSuccess(data=_order_dto(order_row, db))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[BuyerOrder]])
def list_orders(
    status: OrderStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(BuyerOrderRow)

    # Visibility scoping (Section 4.3.1)
    if user.role == "BUYER":
        q = q.filter(BuyerOrderRow.buyer_id == user.user_id)
    elif user.role == "FARMER":
        # Orders on own batches
        batch_ids = [b.id for b in db.query(HarvestBatchRow).filter(
            HarvestBatchRow.farmer_id == user.user_id).all()]
        q = q.filter(BuyerOrderRow.batch_id.in_(batch_ids))
    elif user.role == "LOGISTICS":
        raise ApiError(403, "FORBIDDEN_ROLE", "Logistics cannot access orders",
                       {"requiredRoles": ["BUYER", "FARMER", "ADMIN"], "yourRole": user.role})
    # ADMIN sees all

    if status:
        q = q.filter(BuyerOrderRow.status == status)

    items, next_cursor = paginate(q, BuyerOrderRow, limit, cursor)
    dtos = [_order_dto(r, db) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{order_id}", status_code=200, response_model=ApiSuccess[BuyerOrder])
def get_order(
    order_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(BuyerOrderRow).filter(BuyerOrderRow.id == order_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Order not found",
                       {"resource": "order", "id": str(order_id)})

    # Ownership check
    if user.role == "BUYER" and row.buyer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This order belongs to another buyer",
                       {"resource": "order", "id": str(order_id)})
    elif user.role == "FARMER":
        batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == row.batch_id).first()
        if not batch or batch.farmer_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This order is not on your batch",
                           {"resource": "order", "id": str(order_id)})
    elif user.role == "LOGISTICS":
        raise ApiError(403, "FORBIDDEN_ROLE", "Logistics cannot access orders",
                       {"requiredRoles": ["BUYER", "FARMER", "ADMIN"], "yourRole": user.role})

    return ApiSuccess(data=_order_dto(row, db))


@router.post("/{order_id}/markdown-check", status_code=200,
             response_model=ApiSuccess[MarkdownCheckResult])
def markdown_check(
    order_id: UUID,
    body: MarkdownCheckRequest,
    user: CurrentUser = Depends(require_roles("BUYER")),
    db: Session = Depends(get_db),
):
    order_row = db.query(BuyerOrderRow).filter(BuyerOrderRow.id == order_id).first()
    if not order_row:
        raise ApiError(404, "NOT_FOUND", "Order not found",
                       {"resource": "order", "id": str(order_id)})
    if order_row.buyer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This order belongs to another buyer",
                       {"resource": "order", "id": str(order_id)})
    if order_row.intake_verified_at is None:
        raise ApiError(409, "INTAKE_NOT_VERIFIED",
                       "Intake must be verified before checking markdown",
                       {"orderId": str(order_id)})

    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == order_row.batch_id).first()
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()

    now = datetime.now(timezone.utc)
    result = compute_markdown_check(
        order=order_row,
        batch=batch,
        crop=crop,
        simulate_hours_ahead=body.simulate_hours_ahead,
        now=now,
    )

    if result["newly_triggered"]:
        db.commit()
        db.refresh(order_row)

    # Build webhook payload DTO if present
    webhook_dto = None
    if result["webhook_payload"]:
        webhook_dto = MarkdownWebhookPayload(
            order_id=result["webhook_payload"]["order_id"],
            batch_id=result["webhook_payload"]["batch_id"],
            crop_name=result["webhook_payload"]["crop_name"],
            markdown_pct=result["webhook_payload"]["markdown_pct"],
            shelf_rul_hours=round(result["webhook_payload"]["shelf_rul_hours"], 1),
            triggered_at=result["webhook_payload"]["triggered_at"],
        )

    return ApiSuccess(data=MarkdownCheckResult(
        order=_order_dto(order_row, db),
        shelf_rul_hours=round(result["shelf_rul_hours"], 1),
        threshold_hours=result["threshold_hours"],
        markdown_active=result["markdown_active"],
        newly_triggered=result["newly_triggered"],
        webhook_payload=webhook_dto,
    ))
