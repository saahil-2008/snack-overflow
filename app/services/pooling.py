# app/services/pooling.py — pool compatibility matching (Section 4.3.6)
import math


MAX_PICKUP_RADIUS_KM = 20.0
COHORT_WINDOW_HOURS = 24.0
EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def check_compatibility(
    batch_pickup_lat: float,
    batch_pickup_lng: float,
    batch_ethylene: str,
    batch_rul_hours: float,
    batch_weight_kg: float,
    pool_status: str,
    pool_origin_lat: float,
    pool_origin_lng: float,
    pool_pickup_window_end,
    pool_ethylene_classes: list[str],
    pool_cohort_target_rul_hours: float | None,
    pool_route_tier: str,
    pool_booked_capacity_kg: float,
    pool_max_capacity_kg: float,
    now,
) -> list[str]:
    """Returns list of failing CompatibilityReason strings. Empty = compatible."""
    from app.services.grading import required_route_tier

    reasons = []

    # POOL_NOT_OPEN
    if pool_status != "OPEN" or now >= pool_pickup_window_end:
        reasons.append("POOL_NOT_OPEN")

    # DISTANCE_EXCEEDED
    dist = haversine(batch_pickup_lat, batch_pickup_lng, pool_origin_lat, pool_origin_lng)
    if dist > MAX_PICKUP_RADIUS_KM:
        reasons.append("DISTANCE_EXCEEDED")

    # ETHYLENE_CONFLICT
    if batch_ethylene == "SENSITIVE" and "EMITTER" in pool_ethylene_classes:
        reasons.append("ETHYLENE_CONFLICT")
    elif batch_ethylene == "EMITTER" and "SENSITIVE" in pool_ethylene_classes:
        reasons.append("ETHYLENE_CONFLICT")

    # RUL_OUT_OF_COHORT
    if pool_cohort_target_rul_hours is not None:
        if abs(batch_rul_hours - pool_cohort_target_rul_hours) > COHORT_WINDOW_HOURS:
            reasons.append("RUL_OUT_OF_COHORT")

    # ROUTE_TIER_MISMATCH
    if pool_route_tier != required_route_tier(batch_rul_hours):
        reasons.append("ROUTE_TIER_MISMATCH")

    # CAPACITY_EXCEEDED
    if pool_booked_capacity_kg + batch_weight_kg > pool_max_capacity_kg:
        reasons.append("CAPACITY_EXCEEDED")

    return reasons


def compute_match_score(distance_km: float, rul_delta_hours: float | None) -> float:
    """Score = 1 - (0.5 * distanceKm / 20 + 0.5 * abs(rulDeltaHours ?? 0) / 24)."""
    d_component = 0.5 * distance_km / 20.0
    r_component = 0.5 * abs(rul_delta_hours or 0) / 24.0
    return max(0, 1.0 - d_component - r_component)
