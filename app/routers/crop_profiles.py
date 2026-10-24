# app/routers/crop_profiles.py — crop profile CRUD (Section 4.2)
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user, require_roles
from app.core.errors import ApiError
from app.db.models import CropProfileRow
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, CropProfile, CropProfileUpsertRequest, Paginated, RulCurvePoint, LocalizedText,
)
from app.services.pagination import decode_cursor, encode_cursor

router = APIRouter(prefix="/api/v1/crop-profiles", tags=["crop-profiles"])


def _dto(row: CropProfileRow) -> CropProfile:
    # rul_curve and display_name are stored as camelCase dicts in JSON columns
    rul_curve = [RulCurvePoint.model_validate(p) for p in (row.rul_curve or [])]
    display_name = LocalizedText.model_validate(row.display_name)
    return CropProfile(
        id=row.id,
        crop_name=row.crop_name,
        display_name=display_name,
        ethylene_class=row.ethylene_class,
        harvest_window_days_min=row.harvest_window_days_min,
        harvest_window_days_max=row.harvest_window_days_max,
        heat_stress_temp_c=row.heat_stress_temp_c,
        typical_fruit_mass_g_min=row.typical_fruit_mass_g_min,
        typical_fruit_mass_g_max=row.typical_fruit_mass_g_max,
        stiffness_grade_a_min=row.stiffness_grade_a_min,
        stiffness_grade_b_min=row.stiffness_grade_b_min,
        defect_f0_max_hz=row.defect_f0_max_hz,
        defect_tau_max_ms=row.defect_tau_max_ms,
        rul_curve=rul_curve,
        q10=row.q10,
        reference_temp_c=row.reference_temp_c,
        intake_stiffness_tolerance_pct=row.intake_stiffness_tolerance_pct,
        markdown_threshold_hours=row.markdown_threshold_hours,
        default_markdown_pct=row.default_markdown_pct,
        dispute_tolerance_hours=row.dispute_tolerance_hours,
        calibration_note=row.calibration_note,
        updated_at=row.updated_at,
    )


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[CropProfile]])
def list_crop_profiles(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    _user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Sorted by cropName ascending (special case — not by createdAt)
    q = db.query(CropProfileRow)

    if cursor:
        cursor_dt, cursor_id = decode_cursor(cursor)
        # For crop_name ascending sort, cursor encodes (updated_at, id)
        # but PRD says sort by cropName ascending. We'll use crop_name-based cursor.
        # Actually the PRD says "sorted by cropName ascending" but cursor is still based on standard format.
        # We need to just use a simple approach: fetch all with cropName > last seen, limit+1
        # But cursor format is base64 of "<createdAt>|<id>", let's just use id to filter
        last_row = db.query(CropProfileRow).filter(CropProfileRow.id == cursor_id).first()
        if last_row:
            q = q.filter(
                (CropProfileRow.crop_name > last_row.crop_name) |
                ((CropProfileRow.crop_name == last_row.crop_name) & (CropProfileRow.id > cursor_id))
            )

    q = q.order_by(asc(CropProfileRow.crop_name), asc(CropProfileRow.id))
    rows = q.limit(limit + 1).all()

    if len(rows) > limit:
        items = rows[:limit]
        last = items[-1]
        next_cursor = encode_cursor(last.updated_at, last.id)
    else:
        items = rows
        next_cursor = None

    return ApiSuccess(data=Paginated(items=[_dto(r) for r in items], next_cursor=next_cursor))


@router.get("/{crop_profile_id}", status_code=200, response_model=ApiSuccess[CropProfile])
def get_crop_profile(
    crop_profile_id: UUID,
    _user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(CropProfileRow).filter(CropProfileRow.id == crop_profile_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Crop profile not found",
                       {"resource": "cropProfile", "id": str(crop_profile_id)})
    return ApiSuccess(data=_dto(row))


@router.post("", status_code=201, response_model=ApiSuccess[CropProfile])
def create_crop_profile(
    body: CropProfileUpsertRequest,
    _user: CurrentUser = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    row = CropProfileRow(
        id=uuid4(),
        crop_name=body.crop_name,
        display_name=body.display_name.model_dump(by_alias=True),
        ethylene_class=body.ethylene_class,
        harvest_window_days_min=body.harvest_window_days_min,
        harvest_window_days_max=body.harvest_window_days_max,
        heat_stress_temp_c=body.heat_stress_temp_c,
        typical_fruit_mass_g_min=body.typical_fruit_mass_g_min,
        typical_fruit_mass_g_max=body.typical_fruit_mass_g_max,
        stiffness_grade_a_min=body.stiffness_grade_a_min,
        stiffness_grade_b_min=body.stiffness_grade_b_min,
        defect_f0_max_hz=body.defect_f0_max_hz,
        defect_tau_max_ms=body.defect_tau_max_ms,
        rul_curve=[p.model_dump(by_alias=True) for p in body.rul_curve],
        q10=body.q10,
        reference_temp_c=body.reference_temp_c,
        intake_stiffness_tolerance_pct=body.intake_stiffness_tolerance_pct,
        markdown_threshold_hours=body.markdown_threshold_hours,
        default_markdown_pct=body.default_markdown_pct,
        dispute_tolerance_hours=body.dispute_tolerance_hours,
        calibration_note=body.calibration_note,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_dto(row))


@router.put("/{crop_profile_id}", status_code=200, response_model=ApiSuccess[CropProfile])
def update_crop_profile(
    crop_profile_id: UUID,
    body: CropProfileUpsertRequest,
    _user: CurrentUser = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
):
    row = db.query(CropProfileRow).filter(CropProfileRow.id == crop_profile_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Crop profile not found",
                       {"resource": "cropProfile", "id": str(crop_profile_id)})

    now = datetime.now(timezone.utc)
    row.crop_name = body.crop_name
    row.display_name = body.display_name.model_dump(by_alias=True)
    row.ethylene_class = body.ethylene_class
    row.harvest_window_days_min = body.harvest_window_days_min
    row.harvest_window_days_max = body.harvest_window_days_max
    row.heat_stress_temp_c = body.heat_stress_temp_c
    row.typical_fruit_mass_g_min = body.typical_fruit_mass_g_min
    row.typical_fruit_mass_g_max = body.typical_fruit_mass_g_max
    row.stiffness_grade_a_min = body.stiffness_grade_a_min
    row.stiffness_grade_b_min = body.stiffness_grade_b_min
    row.defect_f0_max_hz = body.defect_f0_max_hz
    row.defect_tau_max_ms = body.defect_tau_max_ms
    row.rul_curve = [p.model_dump(by_alias=True) for p in body.rul_curve]
    row.q10 = body.q10
    row.reference_temp_c = body.reference_temp_c
    row.intake_stiffness_tolerance_pct = body.intake_stiffness_tolerance_pct
    row.markdown_threshold_hours = body.markdown_threshold_hours
    row.default_markdown_pct = body.default_markdown_pct
    row.dispute_tolerance_hours = body.dispute_tolerance_hours
    row.calibration_note = body.calibration_note
    row.updated_at = now

    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_dto(row))
