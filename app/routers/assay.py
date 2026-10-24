# app/routers/assay.py — SonicAssay acoustic scan (Section 4.2, 4.3.4, 4.3.5)
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.core.config import AUDIO_DIR
from app.core.errors import ApiError
from app.db.models import (
    AcousticScanRow, BuyerOrderRow, CropProfileRow, HarvestBatchRow,
    PoolMemberRow, TransportPoolRow, UserRow,
)
from app.db.session import get_db
from app.routers.batches import batch_dto
from app.schemas import (
    AcousticScan, ApiSuccess, ScanMode, ScanStage, SonicScanResult,
)
from app.services.dsp import process_chirp, process_tap, validate_wav
from app.services.grading import (
    check_defect, compute_grade, compute_stiffness, rul_from_curve,
    required_route_tier,
)

router = APIRouter(prefix="/api/v1/assay", tags=["assay"])

MAX_AUDIO_BYTES = 2 * 1024 * 1024  # 2 MB


def _scan_dto(row: AcousticScanRow) -> AcousticScan:
    return AcousticScan.model_validate(row, from_attributes=True)


@router.post("/sonic-scans", response_model=ApiSuccess[SonicScanResult], status_code=201)
async def create_sonic_scan(
    audio: UploadFile = File(...),
    batch_id: UUID = Form(..., alias="batchId"),
    stage: ScanStage = Form(...),
    mode: ScanMode = Form(...),
    client_scan_id: UUID = Form(..., alias="clientScanId"),
    recorded_at: datetime = Form(..., alias="recordedAt"),
    phone_model: str | None = Form(default=None, alias="phoneModel"),
    avg_fruit_mass_g: float | None = Form(default=None, alias="avgFruitMassG"),
    user: CurrentUser = Depends(require_roles("FARMER", "LOGISTICS", "BUYER", "ADMIN")),
    db: Session = Depends(get_db),
) -> ApiSuccess[SonicScanResult]:
    # --- Audio content type and size check ---
    if audio.content_type and audio.content_type not in ("audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"):
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED",
                       "Expected audio/wav",
                       {"receivedContentType": audio.content_type})

    raw = await audio.read()
    if len(raw) > MAX_AUDIO_BYTES:
        raise ApiError(413, "AUDIO_TOO_LARGE",
                       f"Audio file exceeds 2 MB limit ({len(raw)} bytes)",
                       {"maxBytes": MAX_AUDIO_BYTES, "receivedBytes": len(raw)})

    # --- Idempotency check ---
    existing = db.query(AcousticScanRow).filter(
        AcousticScanRow.client_scan_id == client_scan_id
    ).first()
    if existing:
        if existing.scanned_by != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This scan was created by another user",
                           {"resource": "acousticScan", "clientScanId": str(client_scan_id)})
        batch_row = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == existing.batch_id).first()
        # Return 200 with existing scan (note: we override the 201 default)
        from fastapi.responses import JSONResponse
        result = SonicScanResult(scan=_scan_dto(existing), batch=batch_dto(batch_row, db))
        body = ApiSuccess(data=result)
        return JSONResponse(status_code=200, content=body.model_dump(by_alias=True, mode="json"))

    # --- Ownership / state checks ---
    batch_row = db.query(HarvestBatchRow).filter(HarvestBatchRow.id == batch_id).first()
    if not batch_row:
        raise ApiError(404, "NOT_FOUND", "Batch not found",
                       {"resource": "batch", "id": str(batch_id)})

    if stage == "FARM_GATE":
        if user.role != "FARMER":
            raise ApiError(403, "FORBIDDEN_ROLE", "Only farmers can perform FARM_GATE scans",
                           {"requiredRoles": ["FARMER"], "yourRole": user.role})
        if batch_row.farmer_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This batch belongs to another farmer",
                           {"resource": "batch", "id": str(batch_id)})
        if batch_row.status not in ("PENDING_ASSAY", "GRADED"):
            raise ApiError(409, "BATCH_STATE_INVALID",
                           f"Batch status must be PENDING_ASSAY or GRADED for FARM_GATE scan, got {batch_row.status}",
                           {"currentStatus": batch_row.status, "requiredStatuses": ["PENDING_ASSAY", "GRADED"]})
    elif stage == "LOADING":
        if user.role != "LOGISTICS":
            raise ApiError(403, "FORBIDDEN_ROLE", "Only logistics can perform LOADING scans",
                           {"requiredRoles": ["LOGISTICS"], "yourRole": user.role})
        # Check batch is POOLED and the pool belongs to this carrier
        if batch_row.status != "POOLED":
            raise ApiError(409, "BATCH_STATE_INVALID",
                           f"Batch status must be POOLED for LOADING scan, got {batch_row.status}",
                           {"currentStatus": batch_row.status, "requiredStatuses": ["POOLED"]})
        member = db.query(PoolMemberRow).filter(PoolMemberRow.batch_id == batch_id).first()
        if not member:
            raise ApiError(403, "NOT_OWNER", "Batch is not in any pool",
                           {"resource": "batch", "id": str(batch_id)})
        pool = db.query(TransportPoolRow).filter(TransportPoolRow.id == member.pool_id).first()
        if not pool or pool.carrier_id != user.user_id:
            raise ApiError(403, "NOT_OWNER", "This batch's pool is not owned by you",
                           {"resource": "batch", "id": str(batch_id)})
    elif stage == "INTAKE":
        if user.role != "BUYER":
            raise ApiError(403, "FORBIDDEN_ROLE", "Only buyers can perform INTAKE scans",
                           {"requiredRoles": ["BUYER"], "yourRole": user.role})
        if batch_row.status != "ARRIVED":
            raise ApiError(409, "BATCH_STATE_INVALID",
                           f"Batch status must be ARRIVED for INTAKE scan, got {batch_row.status}",
                           {"currentStatus": batch_row.status, "requiredStatuses": ["ARRIVED"]})
        has_order = db.query(BuyerOrderRow).filter(
            BuyerOrderRow.batch_id == batch_id,
            BuyerOrderRow.buyer_id == user.user_id,
        ).first()
        if not has_order:
            raise ApiError(403, "NOT_OWNER", "You have no order on this batch",
                           {"resource": "batch", "id": str(batch_id)})

    # --- WAV decode and DSP ---
    samples, sr = validate_wav(raw)

    if mode == "TAP":
        features = process_tap(samples, sr)
    else:
        features = process_chirp(samples, sr)

    # --- Grading ---
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == batch_row.crop_profile_id).first()
    mass = avg_fruit_mass_g if avg_fruit_mass_g is not None else batch_row.avg_fruit_mass_g
    stiffness = compute_stiffness(features["f0_hz"], mass)
    defect = check_defect(features["f0_hz"], features["tau_ms"],
                          crop.defect_f0_max_hz, crop.defect_tau_max_ms)
    grade = compute_grade(stiffness, crop.stiffness_grade_a_min, crop.stiffness_grade_b_min, defect)
    rul = rul_from_curve(stiffness, crop.rul_curve)

    # --- Store audio file ---
    os.makedirs(AUDIO_DIR, exist_ok=True)
    scan_id = uuid4()
    audio_path = os.path.join(AUDIO_DIR, f"{scan_id}.wav")
    with open(audio_path, "wb") as f:
        f.write(raw)

    now = datetime.now(timezone.utc)

    # Ensure recorded_at is timezone-aware
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)

    scan_row = AcousticScanRow(
        id=scan_id,
        batch_id=batch_id,
        stage=stage,
        mode=mode,
        client_scan_id=client_scan_id,
        f0_hz=features["f0_hz"],
        tap_f0_values_hz=features["tap_f0_values_hz"],
        tap_variation_pct=features.get("tap_variation_pct"),
        spectral_centroid_hz=features["spectral_centroid_hz"],
        tau_ms=features["tau_ms"],
        mfcc_mean=features["mfcc_mean"],
        avg_fruit_mass_g=mass,
        stiffness_index=stiffness,
        estimated_rul_hours=rul,
        grade=grade,
        internal_defect_flag=defect,
        phone_model=phone_model,
        sample_rate_hz=sr,
        audio_path=audio_path,
        scanned_by=user.user_id,
        recorded_at=recorded_at,
        created_at=now,
    )
    db.add(scan_row)

    # --- Batch effects (Section 4.3.5) ---
    if stage == "FARM_GATE":
        # Recompute from ALL farm gate scans for this batch (including the new one)
        db.flush()  # ensure the new scan is in the session
        farm_scans = db.query(AcousticScanRow).filter(
            AcousticScanRow.batch_id == batch_id,
            AcousticScanRow.stage == "FARM_GATE",
        ).all()
        mean_stiffness = sum(s.stiffness_index for s in farm_scans) / len(farm_scans)
        any_defect = any(s.internal_defect_flag for s in farm_scans)
        final_grade = compute_grade(mean_stiffness, crop.stiffness_grade_a_min,
                                    crop.stiffness_grade_b_min, any_defect)
        mean_rul = rul_from_curve(mean_stiffness, crop.rul_curve)

        batch_row.stiffness_index = mean_stiffness
        batch_row.internal_defect_flag = any_defect
        batch_row.quality_grade = final_grade
        batch_row.initial_rul_hours = mean_rul
        batch_row.current_rul_hours = mean_rul
        batch_row.rul_updated_at = now
        batch_row.status = "GRADED"

    elif stage == "LOADING":
        db.flush()
        loading_scans = db.query(AcousticScanRow).filter(
            AcousticScanRow.batch_id == batch_id,
            AcousticScanRow.stage == "LOADING",
        ).all()
        mean_loading_stiffness = sum(s.stiffness_index for s in loading_scans) / len(loading_scans)
        loading_rul = rul_from_curve(mean_loading_stiffness, crop.rul_curve)

        batch_row.loading_stiffness_index = mean_loading_stiffness
        batch_row.current_rul_hours = loading_rul
        batch_row.rul_updated_at = now

    # INTAKE: no batch effect

    db.commit()
    db.refresh(scan_row)
    db.refresh(batch_row)

    return ApiSuccess(data=SonicScanResult(
        scan=_scan_dto(scan_row),
        batch=batch_dto(batch_row, db),
    ))
