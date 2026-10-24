# FarmPool 360 x ChronoCrop — API contract schemas (v1.1.0)
# Backend copy: app/schemas.py. Generated from PRD Section 5. Do not edit by hand.
# Requires: Python >= 3.11, pydantic >= 2.11, < 3.
# snake_case attributes <-> camelCase JSON in both directions via CamelModel.
from datetime import datetime, timezone
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from typing import Annotated, Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)
from pydantic.alias_generators import to_camel


# ───────────────────────── Base model & primitives ─────────────────────────
class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


def _to_utc(v: datetime) -> datetime:
    return v.astimezone(timezone.utc)


def _fmt_utc(v: datetime) -> str:
    return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Accepts only timezone-aware input; always emits "YYYY-MM-DDTHH:MM:SSZ".
UtcDateTime = Annotated[
    AwareDatetime, AfterValidator(_to_utc), PlainSerializer(_fmt_utc, return_type=str)
]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
T = TypeVar("T")


# ───────────────────────── Enums ─────────────────────────
class Role(StrEnum):
    FARMER = "FARMER"
    LOGISTICS = "LOGISTICS"
    BUYER = "BUYER"
    ADMIN = "ADMIN"


class Language(StrEnum):
    EN = "EN"
    HI = "HI"
    MR = "MR"
    TA = "TA"


class Theme(StrEnum):
    LIGHT = "LIGHT"
    DARK = "DARK"
    SYSTEM = "SYSTEM"


class EthyleneClass(StrEnum):
    EMITTER = "EMITTER"
    SENSITIVE = "SENSITIVE"
    NEUTRAL = "NEUTRAL"


class Recommendation(StrEnum):
    HARVEST_NOW = "HARVEST_NOW"
    RECHECK_TOMORROW = "RECHECK_TOMORROW"
    WAIT_48H = "WAIT_48H"


class AdvisoryReasonCode(StrEnum):
    OVERMATURE = "OVERMATURE"
    MATURE_WEATHER_RISK = "MATURE_WEATHER_RISK"
    MATURE_PICKUP_SOON = "MATURE_PICKUP_SOON"
    NEAR_MATURE_RECHECK = "NEAR_MATURE_RECHECK"
    IMMATURE_WAIT = "IMMATURE_WAIT"


class WeatherRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class BatchStatus(StrEnum):
    PENDING_ASSAY = "PENDING_ASSAY"
    GRADED = "GRADED"
    POOLED = "POOLED"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"


class QualityGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class ScanStage(StrEnum):
    FARM_GATE = "FARM_GATE"
    LOADING = "LOADING"
    INTAKE = "INTAKE"


class ScanMode(StrEnum):
    TAP = "TAP"
    CHIRP = "CHIRP"


class RouteTier(StrEnum):
    FAST_QCOMM = "FAST_QCOMM"
    FLEX_REGIONAL = "FLEX_REGIONAL"
    STANDARD_WHOLESALE = "STANDARD_WHOLESALE"


class PoolStatus(StrEnum):
    OPEN = "OPEN"
    IN_TRANSIT = "IN_TRANSIT"
    ARRIVED = "ARRIVED"


class CompatibilityReason(StrEnum):
    POOL_NOT_OPEN = "POOL_NOT_OPEN"
    DISTANCE_EXCEEDED = "DISTANCE_EXCEEDED"
    ETHYLENE_CONFLICT = "ETHYLENE_CONFLICT"
    RUL_OUT_OF_COHORT = "RUL_OUT_OF_COHORT"
    ROUTE_TIER_MISMATCH = "ROUTE_TIER_MISMATCH"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"


class ListingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SOLD_OUT = "SOLD_OUT"
    WITHDRAWN = "WITHDRAWN"


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    INTAKE_ACCEPTED = "INTAKE_ACCEPTED"
    INTAKE_FLAGGED = "INTAKE_FLAGGED"


class IntakeResult(StrEnum):
    ACCEPTED = "ACCEPTED"
    FLAGGED = "FLAGGED"


class ResponsibleParty(StrEnum):
    FARM = "FARM"
    TRANSIT = "TRANSIT"
    BUYER_STORAGE = "BUYER_STORAGE"
    NONE = "NONE"


class CheckpointSource(StrEnum):
    SCAN = "SCAN"
    MODEL = "MODEL"


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
    NOT_OWNER = "NOT_OWNER"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    PHONE_ALREADY_REGISTERED = "PHONE_ALREADY_REGISTERED"
    BATCH_STATE_INVALID = "BATCH_STATE_INVALID"
    POOL_STATE_INVALID = "POOL_STATE_INVALID"
    POOL_INCOMPATIBLE = "POOL_INCOMPATIBLE"
    LISTING_UNAVAILABLE = "LISTING_UNAVAILABLE"
    SCAN_MISMATCH = "SCAN_MISMATCH"
    INTAKE_NOT_VERIFIED = "INTAKE_NOT_VERIFIED"
    INTAKE_ALREADY_VERIFIED = "INTAKE_ALREADY_VERIFIED"
    DISPUTE_ALREADY_EXISTS = "DISPUTE_ALREADY_EXISTS"
    TELEMETRY_OUT_OF_ORDER = "TELEMETRY_OUT_OF_ORDER"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    AUDIO_FORMAT_UNSUPPORTED = "AUDIO_FORMAT_UNSUPPORTED"
    IMPACTS_NOT_DETECTED = "IMPACTS_NOT_DETECTED"
    SCAN_REJECTED_TAP_VARIATION = "SCAN_REJECTED_TAP_VARIATION"
    WEATHER_UNAVAILABLE = "WEATHER_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ───────────────────────── Envelopes ─────────────────────────
class ApiSuccess(CamelModel, Generic[T]):
    success: Literal[True] = True
    data: T


class Paginated(CamelModel, Generic[T]):
    items: list[T]
    next_cursor: str | None


class ValidationFieldError(CamelModel):
    field: str
    message: str
    type: str


class ApiErrorBody(CamelModel):
    code: ErrorCode
    message: str
    details: dict[str, Any]


class ApiErrorResponse(CamelModel):
    success: Literal[False] = False
    error: ApiErrorBody


# ───────────────────────── Shared value objects ─────────────────────────
class LocalizedText(CamelModel):
    en: str = Field(min_length=1, max_length=80)
    hi: str = Field(min_length=1, max_length=80)
    mr: str = Field(min_length=1, max_length=80)
    ta: str = Field(min_length=1, max_length=80)


class RulCurvePoint(CamelModel):
    stiffness_index: float = Field(gt=0)
    rul_hours: float = Field(ge=0)


class HealthStatus(CamelModel):
    status: Literal["OK"] = "OK"
    version: str


# ───────────────────────── Auth & User ─────────────────────────
PHONE_PATTERN = r"^\+[1-9][0-9]{9,14}$"


class User(CamelModel):
    id: UUID
    name: str
    phone: str
    role: Role
    language: Language
    theme: Theme
    organization_name: str | None
    home_latitude: float | None
    home_longitude: float | None
    created_at: UtcDateTime


class RegisterRequest(CamelModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(pattern=PHONE_PATTERN)
    password: str = Field(min_length=8, max_length=72)
    role: Literal[Role.FARMER, Role.LOGISTICS, Role.BUYER]
    language: Language
    organization_name: str | None = Field(min_length=2, max_length=120)


class LoginRequest(CamelModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    password: str = Field(min_length=1, max_length=72)


class AuthResponse(CamelModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: UtcDateTime
    user: User


class UpdateProfileRequest(CamelModel):
    """PATCH: apply only model_dump(exclude_unset=True)."""

    name: str | None = Field(default=None, min_length=2, max_length=80)
    language: Language | None = None
    theme: Theme | None = None
    organization_name: str | None = Field(default=None, min_length=2, max_length=120)
    home_latitude: Latitude | None = None
    home_longitude: Longitude | None = None

    @model_validator(mode="after")
    def _check(self) -> "UpdateProfileRequest":
        for f in ("name", "language", "theme"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{to_camel(f)} cannot be null")
        lat_set = "home_latitude" in self.model_fields_set
        lng_set = "home_longitude" in self.model_fields_set
        if lat_set != lng_set or (self.home_latitude is None) != (self.home_longitude is None):
            raise ValueError("homeLatitude and homeLongitude must be sent together")
        return self


# ───────────────────────── Crop profiles ─────────────────────────
class CropProfileUpsertRequest(CamelModel):
    crop_name: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,49}$")
    display_name: LocalizedText
    ethylene_class: EthyleneClass
    harvest_window_days_min: int = Field(ge=0, le=365)
    harvest_window_days_max: int = Field(ge=1, le=365)
    heat_stress_temp_c: float = Field(ge=20, le=55)
    typical_fruit_mass_g_min: float = Field(gt=0)
    typical_fruit_mass_g_max: float = Field(gt=0)
    stiffness_grade_a_min: float = Field(gt=0)
    stiffness_grade_b_min: float = Field(gt=0)
    defect_f0_max_hz: float = Field(gt=0)
    defect_tau_max_ms: float = Field(gt=0)
    rul_curve: list[RulCurvePoint] = Field(min_length=2)
    q10: float = Field(ge=1, le=5)
    reference_temp_c: float = Field(ge=0, le=40)
    intake_stiffness_tolerance_pct: float = Field(gt=0, le=100)
    markdown_threshold_hours: float = Field(gt=0)
    default_markdown_pct: float = Field(gt=0, le=90)
    dispute_tolerance_hours: float = Field(ge=0)
    calibration_note: str = Field(max_length=500)

    @model_validator(mode="after")
    def _check(self) -> "CropProfileUpsertRequest":
        if self.harvest_window_days_max <= self.harvest_window_days_min:
            raise ValueError("harvestWindowDaysMax must be > harvestWindowDaysMin")
        if self.typical_fruit_mass_g_max <= self.typical_fruit_mass_g_min:
            raise ValueError("typicalFruitMassGMax must be > typicalFruitMassGMin")
        if self.stiffness_grade_a_min <= self.stiffness_grade_b_min:
            raise ValueError("stiffnessGradeAMin must be > stiffnessGradeBMin")
        xs = [p.stiffness_index for p in self.rul_curve]
        if any(b <= a for a, b in zip(xs, xs[1:])):
            raise ValueError("rulCurve must be strictly ascending by stiffnessIndex")
        return self


class CropProfile(CamelModel):
    id: UUID
    crop_name: str
    display_name: LocalizedText
    ethylene_class: EthyleneClass
    harvest_window_days_min: int
    harvest_window_days_max: int
    heat_stress_temp_c: float
    typical_fruit_mass_g_min: float
    typical_fruit_mass_g_max: float
    stiffness_grade_a_min: float
    stiffness_grade_b_min: float
    defect_f0_max_hz: float
    defect_tau_max_ms: float
    rul_curve: list[RulCurvePoint]
    q10: float
    reference_temp_c: float
    intake_stiffness_tolerance_pct: float
    markdown_threshold_hours: float
    default_markdown_pct: float
    dispute_tolerance_hours: float
    calibration_note: str
    updated_at: UtcDateTime


# ───────────────────────── HarvestWindow ─────────────────────────
class HarvestAdvisoryRequest(CamelModel):
    crop_profile_id: UUID
    days_since_flowering: int = Field(ge=0, le=365)
    target_pickup_date: UtcDateTime
    latitude: Latitude
    longitude: Longitude
    simulate_rain_in_hours: int | None = Field(ge=0, le=47)


class HarvestAdvisory(CamelModel):
    id: UUID
    farmer_id: UUID
    crop_profile_id: UUID
    crop_name: str
    days_since_flowering: int
    target_pickup_date: UtcDateTime
    latitude: float
    longitude: float
    maturity_fraction: float
    hours_to_pickup: float
    rain_prob_max_pct: float
    rain_expected_in_hours: float | None
    temp_max_c: float
    humidity_mean_pct: float
    vpd_max_kpa: float
    weather_risk: WeatherRisk
    simulated: bool
    recommendation: Recommendation
    reason_code: AdvisoryReasonCode
    confidence: float
    explanation: str
    override_recommendation: Recommendation | None
    override_reason: str | None
    overridden_by: UUID | None
    overridden_at: UtcDateTime | None
    effective_recommendation: Recommendation
    created_at: UtcDateTime


class AdvisoryOverrideRequest(CamelModel):
    override_recommendation: Recommendation
    override_reason: str = Field(min_length=5, max_length=500)


# ───────────────────────── Batches & scans ─────────────────────────
class CreateBatchRequest(CamelModel):
    crop_profile_id: UUID
    weight_kg: float = Field(gt=0, le=50000)
    avg_fruit_mass_g: float = Field(gt=0, le=20000)
    harvested_at: UtcDateTime
    pickup_latitude: Latitude
    pickup_longitude: Longitude
    harvest_advisory_id: UUID | None


class HarvestBatch(CamelModel):
    id: UUID
    farmer_id: UUID
    farmer_name: str
    crop_profile_id: UUID
    crop_name: str
    ethylene_class: EthyleneClass
    harvest_advisory_id: UUID | None
    weight_kg: float
    avg_fruit_mass_g: float
    harvested_at: UtcDateTime
    pickup_latitude: float
    pickup_longitude: float
    status: BatchStatus
    quality_grade: QualityGrade | None
    internal_defect_flag: bool
    stiffness_index: float | None
    loading_stiffness_index: float | None
    initial_rul_hours: float | None
    current_rul_hours: float | None
    rul_updated_at: UtcDateTime | None
    rul_at_dispatch_hours: float | None
    pool_id: UUID | None
    qr_code_value: str
    created_at: UtcDateTime


class AcousticScan(CamelModel):
    id: UUID
    batch_id: UUID
    stage: ScanStage
    mode: ScanMode
    client_scan_id: UUID
    f0_hz: float
    tap_f0_values_hz: list[float]
    tap_variation_pct: float | None
    spectral_centroid_hz: float
    tau_ms: float
    mfcc_mean: list[float] = Field(min_length=13, max_length=13)
    avg_fruit_mass_g: float
    stiffness_index: float
    estimated_rul_hours: float
    grade: QualityGrade
    internal_defect_flag: bool
    phone_model: str | None
    sample_rate_hz: int
    scanned_by: UUID
    recorded_at: UtcDateTime
    created_at: UtcDateTime


class SonicScanForm(CamelModel):
    """Validated form fields of POST /assay/sonic-scans (the `audio` file is handled separately)."""

    batch_id: UUID
    stage: ScanStage
    mode: ScanMode
    client_scan_id: UUID
    recorded_at: UtcDateTime
    phone_model: str | None = Field(default=None, max_length=80)
    avg_fruit_mass_g: float | None = Field(default=None, gt=0, le=20000)


class SonicScanResult(CamelModel):
    scan: AcousticScan
    batch: HarvestBatch


# ───────────────────────── Pools & telemetry ─────────────────────────
class CreatePoolRequest(CamelModel):
    route_tier: RouteTier
    origin_label: str = Field(min_length=2, max_length=100)
    origin_latitude: Latitude
    origin_longitude: Longitude
    destination_name: str = Field(min_length=2, max_length=100)
    destination_latitude: Latitude
    destination_longitude: Longitude
    max_capacity_kg: float = Field(gt=0, le=40000)
    pickup_window_start: UtcDateTime
    pickup_window_end: UtcDateTime

    @model_validator(mode="after")
    def _check(self) -> "CreatePoolRequest":
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValueError("pickupWindowEnd must be after pickupWindowStart")
        return self


class TransportPool(CamelModel):
    id: UUID
    carrier_id: UUID
    carrier_name: str
    route_tier: RouteTier
    status: PoolStatus
    origin_label: str
    origin_latitude: float
    origin_longitude: float
    destination_name: str
    destination_latitude: float
    destination_longitude: float
    max_capacity_kg: float
    booked_capacity_kg: float
    member_count: int
    cohort_target_rul_hours: float | None
    ethylene_classes: list[EthyleneClass]
    pickup_window_start: UtcDateTime
    pickup_window_end: UtcDateTime
    dispatched_at: UtcDateTime | None
    arrived_at: UtcDateTime | None
    created_at: UtcDateTime


class PoolMember(CamelModel):
    id: UUID
    pool_id: UUID
    batch_id: UUID
    farmer_id: UUID
    farmer_name: str
    crop_name: str
    ethylene_class: EthyleneClass
    kg_booked: float
    current_rul_hours: float | None
    reserved_at: UtcDateTime


class TransportPoolDetail(TransportPool):
    members: list[PoolMember]


class PoolMatchRequest(CamelModel):
    batch_id: UUID


class PoolMatch(CamelModel):
    pool: TransportPool
    distance_km: float
    rul_delta_hours: float | None
    remaining_capacity_kg: float
    score: float


class PoolRejection(CamelModel):
    pool_id: UUID
    reasons: list[CompatibilityReason]


class PoolMatchResult(CamelModel):
    batch_id: UUID
    batch_rul_hours: float
    required_route_tier: RouteTier
    matches: list[PoolMatch]
    rejected: list[PoolRejection]


class CreateReservationRequest(CamelModel):
    batch_id: UUID


class CancelReservationResult(CamelModel):
    pool_id: UUID
    batch_id: UUID
    batch_status: BatchStatus


class TelemetryIngestRequest(CamelModel):
    temp_c: float = Field(ge=-10, le=60)
    latitude: Latitude | None
    longitude: Longitude | None
    recorded_at: UtcDateTime | None


class TelemetryReading(CamelModel):
    id: UUID
    pool_id: UUID
    temp_c: float
    latitude: float | None
    longitude: float | None
    recorded_at: UtcDateTime
    created_at: UtcDateTime


class BatchRulUpdate(CamelModel):
    batch_id: UUID
    previous_rul_hours: float
    decay_factor: float
    consumed_hours: float
    current_rul_hours: float


class TelemetryIngestResult(CamelModel):
    reading: TelemetryReading
    interval_hours: float
    batch_updates: list[BatchRulUpdate]
    reroute_suggested: bool
    suggested_route_tier: RouteTier | None


# ───────────────────────── Marketplace & orders ─────────────────────────
class CreateListingRequest(CamelModel):
    batch_id: UUID
    quantity_kg: float = Field(gt=0, le=50000)
    price_per_kg_inr: float = Field(gt=0, le=100000)


class Listing(CamelModel):
    id: UUID
    batch_id: UUID
    farmer_id: UUID
    farmer_name: str
    crop_profile_id: UUID
    crop_name: str
    quality_grade: QualityGrade
    internal_defect_flag: bool
    quantity_kg: float
    available_kg: float
    price_per_kg_inr: float
    current_rul_hours: float
    route_tier: RouteTier
    guaranteed_arrival_rul_hours: float
    pickup_latitude: float
    pickup_longitude: float
    status: ListingStatus
    created_at: UtcDateTime


class CreateOrderRequest(CamelModel):
    listing_id: UUID
    quantity_kg: float = Field(gt=0, le=50000)


class BuyerOrder(CamelModel):
    id: UUID
    buyer_id: UUID
    buyer_name: str
    listing_id: UUID
    batch_id: UUID
    crop_name: str
    quantity_kg: float
    price_per_kg_inr: float
    total_price_inr: float
    guaranteed_arrival_rul_hours: float
    status: OrderStatus
    intake_scan_id: UUID | None
    intake_result: IntakeResult | None
    intake_stiffness_drop_pct: float | None
    rul_at_intake_hours: float | None
    storage_temp_c: float | None
    intake_verified_at: UtcDateTime | None
    markdown_pct: float
    markdown_triggered_at: UtcDateTime | None
    created_at: UtcDateTime


# ───────────────────────── Intake & markdown ─────────────────────────
class IntakeVerifyRequest(CamelModel):
    order_id: UUID
    scan_id: UUID
    storage_temp_c: float = Field(ge=-5, le=45)


class IntakeVerifyResult(CamelModel):
    order: BuyerOrder
    reference_stiffness_index: float
    intake_stiffness_index: float
    stiffness_drop_pct: float
    tolerance_pct: float
    result: IntakeResult


class MarkdownCheckRequest(CamelModel):
    simulate_hours_ahead: float | None = Field(ge=0, le=240)


class MarkdownWebhookPayload(CamelModel):
    event: Literal["FLASH_MARKDOWN"] = "FLASH_MARKDOWN"
    order_id: UUID
    batch_id: UUID
    crop_name: str
    markdown_pct: float
    shelf_rul_hours: float
    triggered_at: UtcDateTime


class MarkdownCheckResult(CamelModel):
    order: BuyerOrder
    shelf_rul_hours: float
    threshold_hours: float
    markdown_active: bool
    newly_triggered: bool
    webhook_payload: MarkdownWebhookPayload | None


# ───────────────────────── Disputes ─────────────────────────
class CreateDisputeRequest(CamelModel):
    order_id: UUID
    description: str = Field(min_length=10, max_length=1000)


class DisputeSegment(CamelModel):
    party: ResponsibleParty
    start_at: UtcDateTime
    end_at: UtcDateTime
    elapsed_hours: float
    actual_loss_hours: float
    expected_loss_hours: float
    excess_loss_hours: float


class DisputeReport(CamelModel):
    id: UUID
    order_id: UUID
    batch_id: UUID
    raised_by: UUID
    raised_by_role: Role
    description: str
    rul_farm_gate_hours: float
    rul_loading_hours: float
    rul_intake_hours: float
    rul_shelf_hours: float
    farm_gate_at: UtcDateTime
    loading_at: UtcDateTime
    intake_at: UtcDateTime
    assessed_at: UtcDateTime
    loading_checkpoint_source: CheckpointSource
    segments: list[DisputeSegment]
    responsible_party: ResponsibleParty
    created_at: UtcDateTime


# ───────────────────────── Batch passport (public) ─────────────────────────
class BatchPassport(CamelModel):
    batch: HarvestBatch
    scans: list[AcousticScan]
    pool: TransportPool | None
    telemetry: list[TelemetryReading]
