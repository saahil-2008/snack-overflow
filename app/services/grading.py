# app/services/grading.py — stiffness, grade, defect, RUL computation (Section 4.3.4 steps 9–11)
import math


def compute_stiffness(f0_hz: float, avg_fruit_mass_g: float) -> float:
    """Stiffness index S = f0^2 * m^(2/3) where m is in grams."""
    return f0_hz ** 2 * math.pow(avg_fruit_mass_g, 2.0 / 3.0)


def compute_grade(stiffness: float, grade_a_min: float, grade_b_min: float,
                  defect_flag: bool) -> str:
    """Determine quality grade A/B/C. Defect forces C."""
    if defect_flag:
        return "C"
    if stiffness >= grade_a_min:
        return "A"
    if stiffness >= grade_b_min:
        return "B"
    return "C"


def check_defect(f0_hz: float, tau_ms: float,
                 defect_f0_max_hz: float, defect_tau_max_ms: float) -> bool:
    """Internal defect flag: f0 < defectF0MaxHz AND tau < defectTauMaxMs."""
    return f0_hz < defect_f0_max_hz and tau_ms < defect_tau_max_ms


def rul_from_curve(stiffness: float, rul_curve: list[dict]) -> float:
    """Piecewise-linear interpolation over the crop's rulCurve.

    rul_curve is a list of dicts with keys 'stiffnessIndex' and 'rulHours',
    sorted ascending by stiffnessIndex.
    Below the first point → first point's rulHours.
    Above the last → last point's rulHours.
    """
    points = sorted(rul_curve, key=lambda p: p["stiffnessIndex"])

    if stiffness <= points[0]["stiffnessIndex"]:
        return points[0]["rulHours"]
    if stiffness >= points[-1]["stiffnessIndex"]:
        return points[-1]["rulHours"]

    for i in range(len(points) - 1):
        s0 = points[i]["stiffnessIndex"]
        s1 = points[i + 1]["stiffnessIndex"]
        if s0 <= stiffness <= s1:
            r0 = points[i]["rulHours"]
            r1 = points[i + 1]["rulHours"]
            frac = (stiffness - s0) / (s1 - s0)
            return r0 + frac * (r1 - r0)

    return points[-1]["rulHours"]


def required_route_tier(rul_hours: float) -> str:
    """FEFT tier rule: rul < 60 → FAST_QCOMM; 60–120 → FLEX_REGIONAL; > 120 → STANDARD_WHOLESALE."""
    if rul_hours < 60:
        return "FAST_QCOMM"
    if rul_hours <= 120:
        return "FLEX_REGIONAL"
    return "STANDARD_WHOLESALE"


TIER_RANK = {"FAST_QCOMM": 0, "FLEX_REGIONAL": 1, "STANDARD_WHOLESALE": 2}
TIER_TRANSIT_HOURS = {"FAST_QCOMM": 6, "FLEX_REGIONAL": 12, "STANDARD_WHOLESALE": 24}
