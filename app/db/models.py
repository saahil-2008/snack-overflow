from typing import Any
# app/db/models.py — SQLAlchemy 2.x ORM models, column-for-column match to schema.sql (Section 5.4)
from sqlalchemy import Boolean, CheckConstraint, Float, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import JSONType, UTCDateTime, UUIDType


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    name: Mapped[Any] = mapped_column(String(80), nullable=False)
    phone: Mapped[Any] = mapped_column(String(16), nullable=False, unique=True)
    password_hash: Mapped[Any] = mapped_column(String(255), nullable=False)
    role: Mapped[Any] = mapped_column(String(20), nullable=False)
    language: Mapped[Any] = mapped_column(String(2), nullable=False, default="EN")
    theme: Mapped[Any] = mapped_column(String(10), nullable=False, default="SYSTEM")
    organization_name: Mapped[Any] = mapped_column(String(120), nullable=True)
    home_latitude: Mapped[Any] = mapped_column(Float, nullable=True)
    home_longitude: Mapped[Any] = mapped_column(Float, nullable=True)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('FARMER','LOGISTICS','BUYER','ADMIN')", name="ck_users_role"),
        CheckConstraint("language IN ('EN','HI','MR','TA')", name="ck_users_language"),
        CheckConstraint("theme IN ('LIGHT','DARK','SYSTEM')", name="ck_users_theme"),
    )


class CropProfileRow(Base):
    __tablename__ = "crop_profiles"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    crop_name: Mapped[Any] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[Any] = mapped_column(JSONType, nullable=False)
    ethylene_class: Mapped[Any] = mapped_column(String(10), nullable=False)
    harvest_window_days_min: Mapped[Any] = mapped_column(Integer, nullable=False)
    harvest_window_days_max: Mapped[Any] = mapped_column(Integer, nullable=False)
    heat_stress_temp_c: Mapped[Any] = mapped_column(Float, nullable=False)
    typical_fruit_mass_g_min: Mapped[Any] = mapped_column(Float, nullable=False)
    typical_fruit_mass_g_max: Mapped[Any] = mapped_column(Float, nullable=False)
    stiffness_grade_a_min: Mapped[Any] = mapped_column(Float, nullable=False)
    stiffness_grade_b_min: Mapped[Any] = mapped_column(Float, nullable=False)
    defect_f0_max_hz: Mapped[Any] = mapped_column(Float, nullable=False)
    defect_tau_max_ms: Mapped[Any] = mapped_column(Float, nullable=False)
    rul_curve: Mapped[Any] = mapped_column(JSONType, nullable=False)
    q10: Mapped[Any] = mapped_column(Float, nullable=False, default=2.0)
    reference_temp_c: Mapped[Any] = mapped_column(Float, nullable=False, default=25.0)
    intake_stiffness_tolerance_pct: Mapped[Any] = mapped_column(Float, nullable=False, default=15.0)
    markdown_threshold_hours: Mapped[Any] = mapped_column(Float, nullable=False, default=24.0)
    default_markdown_pct: Mapped[Any] = mapped_column(Float, nullable=False, default=20.0)
    dispute_tolerance_hours: Mapped[Any] = mapped_column(Float, nullable=False, default=6.0)
    calibration_note: Mapped[Any] = mapped_column(String(500), nullable=False, default="")
    updated_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("ethylene_class IN ('EMITTER','SENSITIVE','NEUTRAL')", name="ck_crop_ethylene"),
    )


class HarvestAdvisoryRow(Base):
    __tablename__ = "harvest_advisories"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    farmer_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    crop_profile_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    days_since_flowering: Mapped[Any] = mapped_column(Integer, nullable=False)
    target_pickup_date: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    latitude: Mapped[Any] = mapped_column(Float, nullable=False)
    longitude: Mapped[Any] = mapped_column(Float, nullable=False)
    maturity_fraction: Mapped[Any] = mapped_column(Float, nullable=False)
    hours_to_pickup: Mapped[Any] = mapped_column(Float, nullable=False)
    rain_prob_max_pct: Mapped[Any] = mapped_column(Float, nullable=False)
    rain_expected_in_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    temp_max_c: Mapped[Any] = mapped_column(Float, nullable=False)
    humidity_mean_pct: Mapped[Any] = mapped_column(Float, nullable=False)
    vpd_max_kpa: Mapped[Any] = mapped_column(Float, nullable=False)
    weather_risk: Mapped[Any] = mapped_column(String(6), nullable=False)
    simulated: Mapped[Any] = mapped_column(Boolean, nullable=False, default=False)
    recommendation: Mapped[Any] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[Any] = mapped_column(String(30), nullable=False)
    confidence: Mapped[Any] = mapped_column(Float, nullable=False)
    explanation: Mapped[Any] = mapped_column(String(1000), nullable=False)
    override_recommendation: Mapped[Any] = mapped_column(String(20), nullable=True)
    override_reason: Mapped[Any] = mapped_column(String(500), nullable=True)
    overridden_by: Mapped[Any] = mapped_column(UUIDType, nullable=True)
    overridden_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("weather_risk IN ('LOW','MEDIUM','HIGH')", name="ck_advisory_weather_risk"),
        CheckConstraint("recommendation IN ('HARVEST_NOW','RECHECK_TOMORROW','WAIT_48H')", name="ck_advisory_rec"),
        CheckConstraint("reason_code IN ('OVERMATURE','MATURE_WEATHER_RISK','MATURE_PICKUP_SOON','NEAR_MATURE_RECHECK','IMMATURE_WAIT')", name="ck_advisory_reason"),
    )


class HarvestBatchRow(Base):
    __tablename__ = "harvest_batches"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    farmer_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    crop_profile_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    harvest_advisory_id: Mapped[Any] = mapped_column(UUIDType, nullable=True)
    weight_kg: Mapped[Any] = mapped_column(Float, nullable=False)
    avg_fruit_mass_g: Mapped[Any] = mapped_column(Float, nullable=False)
    harvested_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    pickup_latitude: Mapped[Any] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[Any] = mapped_column(Float, nullable=False)
    status: Mapped[Any] = mapped_column(String(20), nullable=False, default="PENDING_ASSAY")
    quality_grade: Mapped[Any] = mapped_column(String(1), nullable=True)
    internal_defect_flag: Mapped[Any] = mapped_column(Boolean, nullable=False, default=False)
    stiffness_index: Mapped[Any] = mapped_column(Float, nullable=True)
    loading_stiffness_index: Mapped[Any] = mapped_column(Float, nullable=True)
    initial_rul_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    current_rul_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    rul_updated_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    rul_at_dispatch_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('PENDING_ASSAY','GRADED','POOLED','IN_TRANSIT','ARRIVED')", name="ck_batch_status"),
        CheckConstraint("quality_grade IN ('A','B','C')", name="ck_batch_grade"),
        Index("ix_batches_farmer", "farmer_id", "created_at"),
    )


class AcousticScanRow(Base):
    __tablename__ = "acoustic_scans"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    batch_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    stage: Mapped[Any] = mapped_column(String(10), nullable=False)
    mode: Mapped[Any] = mapped_column(String(5), nullable=False)
    client_scan_id: Mapped[Any] = mapped_column(UUIDType, nullable=False, unique=True)
    f0_hz: Mapped[Any] = mapped_column(Float, nullable=False)
    tap_f0_values_hz: Mapped[Any] = mapped_column(JSONType, nullable=False)
    tap_variation_pct: Mapped[Any] = mapped_column(Float, nullable=True)
    spectral_centroid_hz: Mapped[Any] = mapped_column(Float, nullable=False)
    tau_ms: Mapped[Any] = mapped_column(Float, nullable=False)
    mfcc_mean: Mapped[Any] = mapped_column(JSONType, nullable=False)
    avg_fruit_mass_g: Mapped[Any] = mapped_column(Float, nullable=False)
    stiffness_index: Mapped[Any] = mapped_column(Float, nullable=False)
    estimated_rul_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    grade: Mapped[Any] = mapped_column(String(1), nullable=False)
    internal_defect_flag: Mapped[Any] = mapped_column(Boolean, nullable=False)
    phone_model: Mapped[Any] = mapped_column(String(80), nullable=True)
    sample_rate_hz: Mapped[Any] = mapped_column(Integer, nullable=False)
    audio_path: Mapped[Any] = mapped_column(String(500), nullable=False)
    scanned_by: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    recorded_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("stage IN ('FARM_GATE','LOADING','INTAKE')", name="ck_scan_stage"),
        CheckConstraint("mode IN ('TAP','CHIRP')", name="ck_scan_mode"),
        CheckConstraint("grade IN ('A','B','C')", name="ck_scan_grade"),
        CheckConstraint("sample_rate_hz IN (44100, 48000)", name="ck_scan_sr"),
        Index("ix_scans_batch", "batch_id", "recorded_at"),
    )


class TransportPoolRow(Base):
    __tablename__ = "transport_pools"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    carrier_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    route_tier: Mapped[Any] = mapped_column(String(20), nullable=False)
    status: Mapped[Any] = mapped_column(String(12), nullable=False, default="OPEN")
    origin_label: Mapped[Any] = mapped_column(String(100), nullable=False)
    origin_latitude: Mapped[Any] = mapped_column(Float, nullable=False)
    origin_longitude: Mapped[Any] = mapped_column(Float, nullable=False)
    destination_name: Mapped[Any] = mapped_column(String(100), nullable=False)
    destination_latitude: Mapped[Any] = mapped_column(Float, nullable=False)
    destination_longitude: Mapped[Any] = mapped_column(Float, nullable=False)
    max_capacity_kg: Mapped[Any] = mapped_column(Float, nullable=False)
    cohort_target_rul_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    pickup_window_start: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    pickup_window_end: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    dispatched_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    arrived_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("route_tier IN ('FAST_QCOMM','FLEX_REGIONAL','STANDARD_WHOLESALE')", name="ck_pool_tier"),
        CheckConstraint("status IN ('OPEN','IN_TRANSIT','ARRIVED')", name="ck_pool_status"),
    )


class PoolMemberRow(Base):
    __tablename__ = "pool_members"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    pool_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    batch_id: Mapped[Any] = mapped_column(UUIDType, nullable=False, unique=True)
    kg_booked: Mapped[Any] = mapped_column(Float, nullable=False)
    reserved_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)


class TelemetryReadingRow(Base):
    __tablename__ = "telemetry_readings"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    pool_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    temp_c: Mapped[Any] = mapped_column(Float, nullable=False)
    latitude: Mapped[Any] = mapped_column(Float, nullable=True)
    longitude: Mapped[Any] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        Index("ix_telemetry_pool", "pool_id", "recorded_at"),
    )


class ListingRow(Base):
    __tablename__ = "listings"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    batch_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    farmer_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    quantity_kg: Mapped[Any] = mapped_column(Float, nullable=False)
    available_kg: Mapped[Any] = mapped_column(Float, nullable=False)
    price_per_kg_inr: Mapped[Any] = mapped_column(Float, nullable=False)
    status: Mapped[Any] = mapped_column(String(10), nullable=False, default="ACTIVE")
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','SOLD_OUT','WITHDRAWN')", name="ck_listing_status"),
        Index("ix_listings_status", "status", "created_at"),
    )


class BuyerOrderRow(Base):
    __tablename__ = "buyer_orders"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    buyer_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    listing_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    batch_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    quantity_kg: Mapped[Any] = mapped_column(Float, nullable=False)
    price_per_kg_inr: Mapped[Any] = mapped_column(Float, nullable=False)
    total_price_inr: Mapped[Any] = mapped_column(Float, nullable=False)
    guaranteed_arrival_rul_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    status: Mapped[Any] = mapped_column(String(16), nullable=False, default="PLACED")
    intake_scan_id: Mapped[Any] = mapped_column(UUIDType, nullable=True)
    intake_result: Mapped[Any] = mapped_column(String(8), nullable=True)
    intake_stiffness_drop_pct: Mapped[Any] = mapped_column(Float, nullable=True)
    rul_at_intake_hours: Mapped[Any] = mapped_column(Float, nullable=True)
    storage_temp_c: Mapped[Any] = mapped_column(Float, nullable=True)
    intake_verified_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    markdown_pct: Mapped[Any] = mapped_column(Float, nullable=False, default=0)
    markdown_triggered_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('PLACED','INTAKE_ACCEPTED','INTAKE_FLAGGED')", name="ck_order_status"),
        Index("ix_orders_buyer", "buyer_id", "created_at"),
    )


class DisputeReportRow(Base):
    __tablename__ = "dispute_reports"

    id: Mapped[Any] = mapped_column(UUIDType, primary_key=True)
    order_id: Mapped[Any] = mapped_column(UUIDType, nullable=False, unique=True)
    batch_id: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    raised_by: Mapped[Any] = mapped_column(UUIDType, nullable=False)
    raised_by_role: Mapped[Any] = mapped_column(String(20), nullable=False)
    description: Mapped[Any] = mapped_column(String(1000), nullable=False)
    rul_farm_gate_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    rul_loading_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    rul_intake_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    rul_shelf_hours: Mapped[Any] = mapped_column(Float, nullable=False)
    farm_gate_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    loading_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    intake_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    assessed_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)
    loading_checkpoint_source: Mapped[Any] = mapped_column(String(5), nullable=False)
    segments: Mapped[Any] = mapped_column(JSONType, nullable=False)
    responsible_party: Mapped[Any] = mapped_column(String(13), nullable=False)
    created_at: Mapped[Any] = mapped_column(UTCDateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("raised_by_role IN ('FARMER','LOGISTICS','BUYER','ADMIN')", name="ck_dispute_role"),
        CheckConstraint("loading_checkpoint_source IN ('SCAN','MODEL')", name="ck_dispute_source"),
        CheckConstraint("responsible_party IN ('FARM','TRANSIT','BUYER_STORAGE','NONE')", name="ck_dispute_party"),
    )
