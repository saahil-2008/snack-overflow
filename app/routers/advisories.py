# app/routers/advisories.py — HarvestWindow advisories (Section 4.2, 4.3.3)
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles, current_user
from app.core.errors import ApiError
from app.db.models import CropProfileRow, HarvestAdvisoryRow, UserRow
from app.db.session import get_db
from app.schemas import (
    AdvisoryOverrideRequest, ApiSuccess, HarvestAdvisory, HarvestAdvisoryRequest,
    Paginated,
)
from app.services.pagination import paginate
from app.services.weather import apply_rain_simulation, fetch_forecast, summarize_weather

router = APIRouter(prefix="/api/v1/harvest-advisories", tags=["harvest-advisories"])


def _dto(row: HarvestAdvisoryRow, crop_name: str) -> HarvestAdvisory:
    effective = row.override_recommendation if row.override_recommendation else row.recommendation
    return HarvestAdvisory(
        id=row.id,
        farmer_id=row.farmer_id,
        crop_profile_id=row.crop_profile_id,
        crop_name=crop_name,
        days_since_flowering=row.days_since_flowering,
        target_pickup_date=row.target_pickup_date,
        latitude=row.latitude,
        longitude=row.longitude,
        maturity_fraction=round(row.maturity_fraction, 2),
        hours_to_pickup=round(row.hours_to_pickup, 1),
        rain_prob_max_pct=round(row.rain_prob_max_pct, 1),
        rain_expected_in_hours=round(row.rain_expected_in_hours, 1) if row.rain_expected_in_hours is not None else None,
        temp_max_c=round(row.temp_max_c, 1),
        humidity_mean_pct=round(row.humidity_mean_pct, 1),
        vpd_max_kpa=round(row.vpd_max_kpa, 1),
        weather_risk=row.weather_risk,
        simulated=row.simulated,
        recommendation=row.recommendation,
        reason_code=row.reason_code,
        confidence=round(row.confidence, 2),
        explanation=row.explanation,
        override_recommendation=row.override_recommendation,
        override_reason=row.override_reason,
        overridden_by=row.overridden_by,
        overridden_at=row.overridden_at,
        effective_recommendation=effective,
        created_at=row.created_at,
    )


@router.post("", status_code=201, response_model=ApiSuccess[HarvestAdvisory])
async def create_advisory(
    body: HarvestAdvisoryRequest,
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    # Validate crop profile exists
    crop = db.query(CropProfileRow).filter(CropProfileRow.id == body.crop_profile_id).first()
    if not crop:
        raise ApiError(404, "NOT_FOUND", "Crop profile not found",
                       {"resource": "cropProfile", "id": str(body.crop_profile_id)})

    now = datetime.now(timezone.utc)

    # Validate targetPickupDate is in the future and ≤ 14 days ahead
    if body.target_pickup_date <= now:
        raise ApiError(422, "VALIDATION_ERROR", "Request validation failed",
                       {"fields": [{"field": "targetPickupDate",
                                    "message": "Target pickup date must be in the future",
                                    "type": "value_error"}]})
    if body.target_pickup_date > now + timedelta(days=14):
        raise ApiError(422, "VALIDATION_ERROR", "Request validation failed",
                       {"fields": [{"field": "targetPickupDate",
                                    "message": "Target pickup date must be within 14 days",
                                    "type": "value_error"}]})

    hours_to_pickup = (body.target_pickup_date - now).total_seconds() / 3600.0

    # Fetch weather
    weather = await fetch_forecast(body.latitude, body.longitude, body.simulate_rain_in_hours)

    # If from baseline, use crop reference temp
    if weather.get("from_baseline"):
        weather["temperature"] = [crop.reference_temp_c] * 48

    simulated = False
    if body.simulate_rain_in_hours is not None:
        weather = apply_rain_simulation(weather, body.simulate_rain_in_hours)
        simulated = True

    summary = summarize_weather(weather)

    # Weather risk
    if summary["rain_prob_max_pct"] >= 60 or summary["temp_max_c"] >= crop.heat_stress_temp_c:
        weather_risk = "HIGH"
    elif summary["rain_prob_max_pct"] >= 30:
        weather_risk = "MEDIUM"
    else:
        weather_risk = "LOW"

    # Maturity fraction
    maturity_fraction = min(1.5, body.days_since_flowering / crop.harvest_window_days_max)

    # Decision rules R1–R5
    if maturity_fraction >= 1.0:
        recommendation, reason_code, base_confidence = "HARVEST_NOW", "OVERMATURE", 0.90
    elif maturity_fraction >= 0.85 and weather_risk == "HIGH":
        recommendation, reason_code, base_confidence = "HARVEST_NOW", "MATURE_WEATHER_RISK", 0.80
    elif maturity_fraction >= 0.85 and hours_to_pickup <= 24:
        recommendation, reason_code, base_confidence = "HARVEST_NOW", "MATURE_PICKUP_SOON", 0.75
    elif maturity_fraction >= 0.60:
        recommendation, reason_code, base_confidence = "RECHECK_TOMORROW", "NEAR_MATURE_RECHECK", 0.65
    else:
        recommendation, reason_code, base_confidence = "WAIT_48H", "IMMATURE_WAIT", 0.85

    confidence = base_confidence - 0.10 if weather_risk == "MEDIUM" else base_confidence

    # Explanation templates
    maturity_pct = round(maturity_fraction * 100)
    explanations = {
        "OVERMATURE": f"Crop is at {maturity_pct}% of its harvest window. Harvest now to avoid over-ripening.",
        "MATURE_WEATHER_RISK": f"Crop is at {maturity_pct}% maturity and the next 48 h carry high weather risk (rain up to {round(summary['rain_prob_max_pct'], 1)}%, max {round(summary['temp_max_c'], 1)} °C). Harvest before the weather turns.",
        "MATURE_PICKUP_SOON": f"Crop is at {maturity_pct}% maturity and pickup is in {round(hours_to_pickup, 1)} h. Harvest now to meet the pickup.",
        "NEAR_MATURE_RECHECK": f"Crop is at {maturity_pct}% maturity. Weather risk is {weather_risk}. Recheck tomorrow.",
        "IMMATURE_WAIT": f"Crop is at {maturity_pct}% maturity. Wait about 48 h before checking again.",
    }
    explanation = explanations[reason_code]

    advisory_id = uuid4()
    row = HarvestAdvisoryRow(
        id=advisory_id,
        farmer_id=user.user_id,
        crop_profile_id=body.crop_profile_id,
        days_since_flowering=body.days_since_flowering,
        target_pickup_date=body.target_pickup_date,
        latitude=body.latitude,
        longitude=body.longitude,
        maturity_fraction=maturity_fraction,
        hours_to_pickup=hours_to_pickup,
        rain_prob_max_pct=summary["rain_prob_max_pct"],
        rain_expected_in_hours=summary["rain_expected_in_hours"],
        temp_max_c=summary["temp_max_c"],
        humidity_mean_pct=summary["humidity_mean_pct"],
        vpd_max_kpa=summary["vpd_max_kpa"],
        weather_risk=weather_risk,
        simulated=simulated,
        recommendation=recommendation,
        reason_code=reason_code,
        confidence=confidence,
        explanation=explanation,
        override_recommendation=None,
        override_reason=None,
        overridden_by=None,
        overridden_at=None,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ApiSuccess(data=_dto(row, crop.crop_name))


@router.get("", status_code=200, response_model=ApiSuccess[Paginated[HarvestAdvisory]])
def list_advisories(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    user: CurrentUser = Depends(require_roles("FARMER")),
    db: Session = Depends(get_db),
):
    q = db.query(HarvestAdvisoryRow).filter(HarvestAdvisoryRow.farmer_id == user.user_id)
    items, next_cursor = paginate(q, HarvestAdvisoryRow, limit, cursor)

    # Get crop names
    crop_ids = {r.crop_profile_id for r in items}
    crops = {c.id: c.crop_name for c in db.query(CropProfileRow).filter(CropProfileRow.id.in_(crop_ids)).all()} if crop_ids else {}

    dtos = [_dto(r, crops.get(r.crop_profile_id, "UNKNOWN")) for r in items]
    return ApiSuccess(data=Paginated(items=dtos, next_cursor=next_cursor))


@router.get("/{advisory_id}", status_code=200, response_model=ApiSuccess[HarvestAdvisory])
def get_advisory(
    advisory_id: UUID,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(HarvestAdvisoryRow).filter(HarvestAdvisoryRow.id == advisory_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Advisory not found",
                       {"resource": "harvestAdvisory", "id": str(advisory_id)})

    # FARMER can see own, ADMIN can see all
    if user.role == "FARMER" and row.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This advisory belongs to another farmer",
                       {"resource": "harvestAdvisory", "id": str(advisory_id)})
    if user.role not in ("FARMER", "ADMIN"):
        raise ApiError(403, "FORBIDDEN_ROLE", "Your role cannot access advisories",
                       {"requiredRoles": ["FARMER", "ADMIN"], "yourRole": user.role})

    crop = db.query(CropProfileRow).filter(CropProfileRow.id == row.crop_profile_id).first()
    crop_name = crop.crop_name if crop else "UNKNOWN"
    return ApiSuccess(data=_dto(row, crop_name))


@router.post("/{advisory_id}/override", status_code=200, response_model=ApiSuccess[HarvestAdvisory])
def override_advisory(
    advisory_id: UUID,
    body: AdvisoryOverrideRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.query(HarvestAdvisoryRow).filter(HarvestAdvisoryRow.id == advisory_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "Advisory not found",
                       {"resource": "harvestAdvisory", "id": str(advisory_id)})

    # FARMER owner or ADMIN
    if user.role == "FARMER" and row.farmer_id != user.user_id:
        raise ApiError(403, "NOT_OWNER", "This advisory belongs to another farmer",
                       {"resource": "harvestAdvisory", "id": str(advisory_id)})
    if user.role not in ("FARMER", "ADMIN"):
        raise ApiError(403, "FORBIDDEN_ROLE", "Your role cannot override advisories",
                       {"requiredRoles": ["FARMER", "ADMIN"], "yourRole": user.role})

    now = datetime.now(timezone.utc)
    row.override_recommendation = body.override_recommendation
    row.override_reason = body.override_reason
    row.overridden_by = user.user_id
    row.overridden_at = now

    db.commit()
    db.refresh(row)

    crop = db.query(CropProfileRow).filter(CropProfileRow.id == row.crop_profile_id).first()
    crop_name = crop.crop_name if crop else "UNKNOWN"
    return ApiSuccess(data=_dto(row, crop_name))
