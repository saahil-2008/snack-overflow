# app/services/decay.py — Q10 decay model for telemetry and shelf RUL (Sections 4.3.7, 4.3.9)


def q10_decay_factor(q10: float, temp_c: float, reference_temp_c: float) -> float:
    """Q10 decay factor = q10 ^ ((tempC - referenceTempC) / 10)."""
    return q10 ** ((temp_c - reference_temp_c) / 10.0)


def consumed_hours(interval_hours: float, decay_factor: float) -> float:
    """Hours of RUL consumed = intervalHours × decayFactor."""
    return interval_hours * decay_factor


def shelf_rul(
    rul_at_intake_hours: float,
    intake_verified_at,
    now,
    storage_temp_c: float,
    q10: float,
    reference_temp_c: float,
) -> float:
    """Shelf RUL at time t = max(0, rulAtIntakeHours - hours(t - intakeVerifiedAt) * q10^(...))."""
    elapsed = (now - intake_verified_at).total_seconds() / 3600.0
    factor = q10_decay_factor(q10, storage_temp_c, reference_temp_c)
    return max(0.0, rul_at_intake_hours - elapsed * factor)
