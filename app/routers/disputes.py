# app/routers/disputes.py — Dispute ledger (Section 4.2, 4.3.10)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user, require_roles
from app.core.errors import ApiError
from app.db.models import (
    AcousticScanRow, BuyerOrderRow, CropProfileRow, DisputeReportRow,
    HarvestBatchRow, PoolMemberRow, TransportPoolRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, CreateDisputeRequest, DisputeReport, DisputeSegment, Paginated,
)
from app.services.disputes import build_dispute
from app.services.pagination import paginate

router = APIRouter(prefix="/api/v1/disputes", tags=["disputes"])


def _dispute_dto(row: DisputeReportRow) -> DisputeReport:
    segments = [DisputeSegment.model_validate(s) for s in (row.segments or [])]
    return DisputeReport(
        id=row.id,
        order_id=row.order_id,
        batch_id=row.batch_id,
        raised_by=row.raised_by,
        raised_by_role=row.raised_by_role,
        description=row.description,
        rul_farm_gate_hours=round(row.rul_farm_gate_hours, 1),
        rul_loading_hours=round(row.rul_loading_hours, 1),
        rul_intake_hours=round(row.rul_intake_hours, 1),
        rul_shelf_hours=round(row.rul_shelf_hours, 1),
        farm_gate_at=row.farm_gate_at,
        loading_at=row.loading_at,
        intake_at=row.intake_at,
        assessed_at=row.assessed_at,
        loading_checkpoint_source=row.loading_checkpoint_source,
        segments=segments,
        responsible_party=row.responsible_party,
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ApiSuccess[DisputeReport])
def create_dispute(
    body: CreateDisputeRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Caller must be buyer of the order or farmer of the batch
    order = db.query(BuyerOrderRow).filter(BuyerOrderRow.id == body.order_id).first()
    if not order:
        raise ApiError(404, "NOT_FOUND", "Order not found",
                       {"resource": "order", "id": str(body.order_id)})

    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == order.batch_id).first()

    if user.role == "BUYER" and order.buyer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This order belongs to another buyer",
                       {"resource": "order", "id": str(body.order_id)})
    elif user.role == "FARMER" and (not batch or batch.farmer_id != user.user_id):
        raise ApiError(403, "NOT_OWNER", "This order is not on your batch",
                       {"resource": "order", "id": str(body.order_id)})
    elif user.role == "LOGISTICS":
        raise ApiError(403, "FORBIDDEN_ROLE", "Logistics cannot create disputes",
                       {"requiredRoles": ["BUYER", "FARMER", "ADMIN"], "yourRole": user.role})

    # Intake must be verified
    if order.intake_verified_at is None:
        raise ApiError(409, "INTAKE_NOT_VERIFIED",
                       "Intake must be verified before filing a dispute",
                       {"orderId": str(body.order_id)})

    # One dispute per order
    existing = db.query(DisputeReportRow).filter(DisputeReportRow.order_id == body.order_id).first()
    if existing:
        raise ApiError(409, "DISPUTE_ALREADY_EXISTS",
                       "A dispute already exists for this order",
                       {"existingDisputeId": str(existing.id)})

    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()
    scans = db.query(AcousticScanRow).filter(
        AcousticScanRow.batch_id == order.batch_id
    ).order_by(AcousticScanRow.recorded_at).all()

    # Get pool if any
    member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == order.batch_id).first()
    pool = None
    if member:
        pool = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()

    now = datetime.now(timezone.utc)
    dispute_data = build_dispute(order, batch, crop, scans, pool, now)

    # Serialize segment dicts for storage (with camelCase keys for Pydantic)
    segments_for_db = []
    for seg in dispute_data["segments"]:
        segments_for_db.append({
            "party": seg["party"],
            "startAt": seg["start_at"].isoformat() if hasattr(seg["start_at"], "isoformat") else str(seg["start_at"]),
            "endAt": seg["end_at"].isoformat() if hasattr(seg["end_at"], "isoformat") else str(seg["end_at"]),
            "elapsedHours": round(seg["elapsed_hours"], 1),
            "actualLossHours": round(seg["actual_loss_hours"], 1),
            "expectedLossHours": round(seg["expected_loss_hours"], 1),
            "excessLossHours": round(seg["excess_loss_hours"], 1),
        })

    dispute_id = uuid4()
    dispute_row = DisputeReportRow(
        id=dispute_id,
        order_id=body.order_id,
        batch_id=order.batch_id,
        raised_by=user.user_id,
        raised_by_role=user.role,
        description=body.description,
        rul_farm_gate_hours=dispute_data["rul_farm_gate_hours"],
        rul_loading_hours=dispute_data["rul_loading_hours"],
        rul_intake_hours=dispute_data["rul_intake_hours"],
        rul_shelf_hours=dispute_data["rul_shelf_hours"],
        farm_gate_at=dispute_data["farm_gate_at"],
        loading_at=dispute_data["loading_at"],
        intake_at=dispute_data["intake_at"],
        assessed_at=dispute_data["assessed_at"],
        loading_checkpoint_source=dispute_data["loading_checkpoint_source"],
        segments=segments_for_db,
        responsible_party=dispute_data["responsible_party"],
        created_at=now,
    )
    db.add(dispute_row)
    db.commit()
    db.refresh(dispute_row)

    return ApiSuccess(data=_dispute_dto(dispute_row))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[DisputeReport]])
def list_disputes(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DisputeReportRow)

    # Visibility scoping (Section 4.3.1)
    if user.role == "BUYER":
        order_ids = [o.id for o in db.query(BuyerOrderRow).filter(
            BuyerOrderRow.buyer_id == user.user_id).all()]
        q = q.filter(DisputeReportRow.order_id.in_(order_ids))
    elif user.role == "FARMER":
        batch_ids = [b.id for b in db.query(HarvestBatchRow).filter(
            HarvestBatchRow.farmer_id == user.user_id).all()]
        q = q.filter(DisputeReportRow.batch_id.in_(batch_ids))
    elif user.role == "LOGISTICS":
        raise ApiError(403, "FORBIDDEN_ROLE", "Logistics cannot access disputes",
                       {"requiredRoles": ["BUYER", "FARMER", "ADMIN"], "yourRole": user.role})
    # ADMIN sees all

    items, next_cursor = paginate(q, DisputeReportRow, limit, cursor)
    dtos = [_dispute_dto(r) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{dispute_id}", status_code=200, response_model=ApiSuccess[DisputeReport])
def get_dispute(
    dispute_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(DisputeReportRow).filter(DisputeReportRow.id == dispute_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Dispute not found",
                       {"resource": "dispute", "id": str(dispute_id)})

    # Ownership check
    if user.role == "BUYER":
        order = db.query(BuyerOrderRow).filter(BuyerOrderRow.id == row.order_id).first()
        if not order or order.buyer_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This dispute is not on your order",
                           {"resource": "dispute", "id": str(dispute_id)})
    elif user.role == "FARMER":
        batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == row.batch_id).first()
        if not batch or batch.farmer_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This dispute is not on your batch",
                           {"resource": "dispute", "id": str(dispute_id)})
    elif user.role == "LOGISTICS":
        raise ApiError(403, "FORBIDDEN_ROLE", "Logistics cannot access disputes",
                       {"requiredRoles": ["BUYER", "FARMER", "ADMIN"], "yourRole": user.role})

    return ApiSuccess(data=_dispute_dto(row))
