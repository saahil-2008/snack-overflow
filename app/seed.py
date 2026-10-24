# app/seed.py — Demo seed data (PRD Section 6.4)
# Inserts when SEED_DEMO=true and users table is empty.
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from sqlalchemy.orm import Session

from app.db.models import CropProfileRow, TransportPoolRow, UserRow

log = logging.getLogger("farmpool")

DEMO_PASSWORD = "Demo@12345"


def _hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def seed_demo_data(db: Session) -> None:
    """Seed demo data if the users table is empty."""
    if db.query(UserRow).first() is not None:
        log.info("Seed skipped: users table is not empty")
        return

    log.info("Seeding demo data...")
    now = datetime.now(timezone.utc)
    pw_hash = _hash_pw(DEMO_PASSWORD)

    # ─── Users ───
    farmer_id = uuid4()
    logistics_id = uuid4()
    buyer_id = uuid4()
    admin_id = uuid4()

    users = [
        UserRow(
            id=farmer_id, name="Ramesh Pawar", phone="+919800000001",
            password_hash=pw_hash, role="FARMER", language="HI", theme="SYSTEM",
            organization_name="Pimpalgaon Tomato FPO",
            home_latitude=20.166700, home_longitude=73.983300,
            created_at=now,
        ),
        UserRow(
            id=logistics_id, name="Sunita Logistics", phone="+919800000002",
            password_hash=pw_hash, role="LOGISTICS", language="EN", theme="SYSTEM",
            organization_name="Sahyadri Reefer Lines",
            home_latitude=20.011000, home_longitude=73.790000,
            created_at=now,
        ),
        UserRow(
            id=buyer_id, name="Arjun Mehta", phone="+919800000003",
            password_hash=pw_hash, role="BUYER", language="EN", theme="SYSTEM",
            organization_name="Nashik Road Dark Store 4",
            home_latitude=19.954800, home_longitude=73.837000,
            created_at=now,
        ),
        UserRow(
            id=admin_id, name="Dr. Kavita Rao", phone="+919800000004",
            password_hash=pw_hash, role="ADMIN", language="EN", theme="SYSTEM",
            organization_name="FarmPool Agronomy",
            home_latitude=None, home_longitude=None,
            created_at=now,
        ),
    ]
    db.add_all(users)

    # ─── Crop Profiles ───
    cal_note = "Placeholder calibration — replace with hackathon validation data"

    crop_profiles = [
        CropProfileRow(
            id=uuid4(), crop_name="TOMATO",
            display_name={"en": "Tomato", "hi": "टमाटर", "mr": "टोमॅटो", "ta": "தக்காளி"},
            ethylene_class="EMITTER",
            harvest_window_days_min=40, harvest_window_days_max=55,
            heat_stress_temp_c=35, typical_fruit_mass_g_min=80, typical_fruit_mass_g_max=200,
            stiffness_grade_a_min=3500000, stiffness_grade_b_min=2000000,
            defect_f0_max_hz=220, defect_tau_max_ms=6.0,
            rul_curve=[
                {"stiffnessIndex": 1000000, "rulHours": 24},
                {"stiffnessIndex": 2000000, "rulHours": 60},
                {"stiffnessIndex": 3000000, "rulHours": 110},
                {"stiffnessIndex": 4500000, "rulHours": 160},
            ],
            q10=2.5, reference_temp_c=25,
            intake_stiffness_tolerance_pct=15, markdown_threshold_hours=24,
            default_markdown_pct=20, dispute_tolerance_hours=6,
            calibration_note=cal_note, updated_at=now,
        ),
        CropProfileRow(
            id=uuid4(), crop_name="MANGO",
            display_name={"en": "Mango", "hi": "आम", "mr": "आंबा", "ta": "மாம்பழம்"},
            ethylene_class="EMITTER",
            harvest_window_days_min=90, harvest_window_days_max=120,
            heat_stress_temp_c=38, typical_fruit_mass_g_min=180, typical_fruit_mass_g_max=350,
            stiffness_grade_a_min=2000000, stiffness_grade_b_min=1200000,
            defect_f0_max_hz=140, defect_tau_max_ms=5.0,
            rul_curve=[
                {"stiffnessIndex": 600000, "rulHours": 24},
                {"stiffnessIndex": 1200000, "rulHours": 72},
                {"stiffnessIndex": 2000000, "rulHours": 120},
                {"stiffnessIndex": 3000000, "rulHours": 168},
            ],
            q10=2.2, reference_temp_c=25,
            intake_stiffness_tolerance_pct=15, markdown_threshold_hours=24,
            default_markdown_pct=20, dispute_tolerance_hours=6,
            calibration_note=cal_note, updated_at=now,
        ),
        CropProfileRow(
            id=uuid4(), crop_name="CUCUMBER",
            display_name={"en": "Cucumber", "hi": "खीरा", "mr": "काकडी", "ta": "வெள்ளரிக்காய்"},
            ethylene_class="SENSITIVE",
            harvest_window_days_min=10, harvest_window_days_max=18,
            heat_stress_temp_c=35, typical_fruit_mass_g_min=150, typical_fruit_mass_g_max=400,
            stiffness_grade_a_min=5000000, stiffness_grade_b_min=3000000,
            defect_f0_max_hz=250, defect_tau_max_ms=5.0,
            rul_curve=[
                {"stiffnessIndex": 2000000, "rulHours": 24},
                {"stiffnessIndex": 3000000, "rulHours": 60},
                {"stiffnessIndex": 5000000, "rulHours": 120},
                {"stiffnessIndex": 7000000, "rulHours": 168},
            ],
            q10=2.0, reference_temp_c=25,
            intake_stiffness_tolerance_pct=15, markdown_threshold_hours=24,
            default_markdown_pct=20, dispute_tolerance_hours=6,
            calibration_note=cal_note, updated_at=now,
        ),
        CropProfileRow(
            id=uuid4(), crop_name="WATERMELON",
            display_name={"en": "Watermelon", "hi": "तरबूज", "mr": "कलिंगड", "ta": "தர்பூசணி"},
            ethylene_class="SENSITIVE",
            harvest_window_days_min=30, harvest_window_days_max=40,
            heat_stress_temp_c=38, typical_fruit_mass_g_min=3000, typical_fruit_mass_g_max=8000,
            stiffness_grade_a_min=6000000, stiffness_grade_b_min=4000000,
            defect_f0_max_hz=100, defect_tau_max_ms=8.0,
            rul_curve=[
                {"stiffnessIndex": 3000000, "rulHours": 48},
                {"stiffnessIndex": 4000000, "rulHours": 120},
                {"stiffnessIndex": 6000000, "rulHours": 240},
                {"stiffnessIndex": 8000000, "rulHours": 336},
            ],
            q10=2.0, reference_temp_c=25,
            intake_stiffness_tolerance_pct=15, markdown_threshold_hours=24,
            default_markdown_pct=20, dispute_tolerance_hours=6,
            calibration_note=cal_note, updated_at=now,
        ),
        CropProfileRow(
            id=uuid4(), crop_name="POMEGRANATE",
            display_name={"en": "Pomegranate", "hi": "अनार", "mr": "डाळिंब", "ta": "மாதுளை"},
            ethylene_class="NEUTRAL",
            harvest_window_days_min=120, harvest_window_days_max=150,
            heat_stress_temp_c=40, typical_fruit_mass_g_min=200, typical_fruit_mass_g_max=400,
            stiffness_grade_a_min=3500000, stiffness_grade_b_min=2200000,
            defect_f0_max_hz=180, defect_tau_max_ms=5.0,
            rul_curve=[
                {"stiffnessIndex": 1500000, "rulHours": 72},
                {"stiffnessIndex": 2200000, "rulHours": 168},
                {"stiffnessIndex": 3500000, "rulHours": 336},
                {"stiffnessIndex": 5000000, "rulHours": 480},
            ],
            q10=2.0, reference_temp_c=25,
            intake_stiffness_tolerance_pct=15, markdown_threshold_hours=24,
            default_markdown_pct=20, dispute_tolerance_hours=6,
            calibration_note=cal_note, updated_at=now,
        ),
    ]
    db.add_all(crop_profiles)

    # ─── Pools ───
    # carrier = Sunita Logistics, origin "Pimpalgaon cluster" 20.166700, 73.983300
    # capacity 4000 kg, pickup window = now + 12h → now + 36h
    window_start = now + timedelta(hours=12)
    window_end = now + timedelta(hours=36)

    pools = [
        TransportPoolRow(
            id=uuid4(), carrier_id=logistics_id,
            route_tier="FAST_QCOMM", status="OPEN",
            origin_label="Pimpalgaon cluster",
            origin_latitude=20.166700, origin_longitude=73.983300,
            destination_name="Nashik Road Dark Store 4",
            destination_latitude=19.954800, destination_longitude=73.837000,
            max_capacity_kg=4000, cohort_target_rul_hours=None,
            pickup_window_start=window_start, pickup_window_end=window_end,
            dispatched_at=None, arrived_at=None, created_at=now,
        ),
        TransportPoolRow(
            id=uuid4(), carrier_id=logistics_id,
            route_tier="FLEX_REGIONAL", status="OPEN",
            origin_label="Pimpalgaon cluster",
            origin_latitude=20.166700, origin_longitude=73.983300,
            destination_name="Vashi APMC, Navi Mumbai",
            destination_latitude=19.079000, destination_longitude=73.009000,
            max_capacity_kg=4000, cohort_target_rul_hours=None,
            pickup_window_start=window_start, pickup_window_end=window_end,
            dispatched_at=None, arrived_at=None, created_at=now,
        ),
        TransportPoolRow(
            id=uuid4(), carrier_id=logistics_id,
            route_tier="STANDARD_WHOLESALE", status="OPEN",
            origin_label="Pimpalgaon cluster",
            origin_latitude=20.166700, origin_longitude=73.983300,
            destination_name="Ahmedabad Jamalpur Market",
            destination_latitude=23.017000, destination_longitude=72.587000,
            max_capacity_kg=4000, cohort_target_rul_hours=None,
            pickup_window_start=window_start, pickup_window_end=window_end,
            dispatched_at=None, arrived_at=None, created_at=now,
        ),
    ]
    db.add_all(pools)

    db.commit()
    log.info("Seed data inserted: 4 users, 5 crop profiles, 3 pools")
