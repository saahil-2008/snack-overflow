# app/routers/intake.py — Dark-store intake verification (Section 4.2, 4.3.9)
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.core.errors import ApiError
from app.db.models import (
    AcousticScanRow, BuyerOrderRow, CropProfileRow, HarvestBatchRow, UserRow,
)
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, BuyerOrder, IntakeResult, IntakeVerifyRequest, IntakeVerifyResult,
)

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])


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


@router.post("/verify", status_code=200, response_model=ApiSuccess[IntakeVerifyResult])
def intake_verify(
    body: IntakeVerifyRequest,
    user: CurrentUser = Depends(require_roles("BUYER")),
    db: Session = Depends(get_db),
):
    order = db.query(BuyerOrderRow).filter(BuyerOrderRow.id == body.order_id).first()
    if not order:
        raise ApiError(404, "NOT_FOUND", "Order not found",
                       {"resource": "order", "id": str(body.order_id)})
    if order.buyer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This order belongs to another buyer",
                       {"resource": "order", "id": str(body.order_id)})
    if order.status != "PLACED":
        raise ApiError(409, "INTAKE_ALREADY_VERIFIED",
                       "Intake has already been verified for this order",
                       {"currentStatus": order.status})

    # Validate scan exists, is INTAKE stage for this batch, created by this user
    scan = db.query(AcousticScanRow).filter(AcousticScanRow.id == body.scan_id).first()
    if not scan:
        raise ApiError(404, "NOT_FOUND", "Scan not found",
                       {"resource": "acousticScan", "id": str(body.scan_id)})
    if scan.stage != "INTAKE" or scan.batch_id != order.batch_id or scan.scanned_by != user.user_id:
        raise ApiError(409, "SCAN_MISMATCH",
                       "Scan must be an INTAKE scan of this order's batch created by you",
                       {"scanId": str(body.scan_id), "scanStage": scan.stage,
                        "scanBatchId": str(scan.batch_id), "orderBatchId": str(order.batch_id)})

    batch = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == order.batch_id).first()
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch.crop_profile_id).first()

    # Reference stiffness: loadingStiffnessIndex if available, else stiffnessIndex
    reference = batch.loading_stiffness_index if batch.loading_stiffness_index is not None else batch.stiffness_index
    if reference is None or reference == 0:
        reference = scan.stiffness_index  # fallback to avoid division by zero

    stiffness_drop_pct = (reference - scan.stiffness_index) / reference * 100
    tolerance_pct = crop.intake_stiffness_tolerance_pct

    if stiffness_drop_pct <= tolerance_pct:
        result = "ACCEPTED"
        order_status = "INTAKE_ACCEPTED"
    else:
        result = "FLAGGED"
        order_status = "INTAKE_FLAGGED"

    now = datetime.now(timezone.utc)
    order.intake_scan_id = body.scan_id
    order.intake_result = result
    order.intake_stiffness_drop_pct = stiffness_drop_pct
    order.rul_at_intake_hours = scan.estimated_rul_hours
    order.storage_temp_c = body.storage_temp_c
    order.intake_verified_at = now
    order.status = order_status

    db.commit()
    db.refresh(order)

    return ApiSuccess(data=IntakeVerifyResult(
        order=_order_dto(order, db),
        reference_stiffness_index=round(reference, 0),
        intake_stiffness_index=round(scan.stiffness_index, 0),
        stiffness_drop_pct=round(stiffness_drop_pct, 1),
        tolerance_pct=tolerance_pct,
        result=result,
    ))
