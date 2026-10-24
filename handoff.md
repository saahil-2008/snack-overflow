# FarmPool 360 × ChronoCrop — Backend Build Handoff

**Conversation ID:** `6722d03a-8522-4ef0-a020-4d23b508c7d2`  
**Last Updated:** `2026-10-24T03:43:00+05:30`  
**PRD Source:** [FarmPool360_ChronoCrop_PRD_v1.1.md](file:///c:/Users/Saahil/Desktop/snack-overflow/FarmPool360_ChronoCrop_PRD_v1.1.md)

> [!IMPORTANT]
> This agent is building **ONLY** the Python FastAPI backend. **ZERO frontend code.** The PRD is the single source of truth. Sections 1.3, 5.2, 6.2 are for a separate frontend agent — ignore them completely.

---

## Current Execution State & Immediate Next Step

- **Last File Completed:** [app/routers/passport.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/passport.py) (public QR passport endpoint `GET /passport/{batchId}`)
- **Next File to Build:** `app/routers/assay.py`
  - Endpoint: `POST /assay/sonic-scans` (PRD Section 4.2 & Section 5.3)
  - Accepts multipart: `file` (UploadFile), `batch_id` (UUID), `scan_type` (ScanType: TAP or CHIRP), `device_model` (str), `idempotency_key` (UUID)
  - Reads WAV audio, runs `validate_wav()` and `run_pipeline()` from `app.services.dsp`
  - Resolves `CropProfile` from batch to invoke `compute_grade_and_rul()` from `app.services.grading`
  - Stores `AcousticScan` record in DB with audio checksum and idempotent key verification
  - Updates `HarvestBatch` status (`ASSAYED`), stiffness, resonant frequency, quality grade, internal defect flag, route tier, and initial RUL
  - Returns `ApiSuccess[ScanResponse]`

---

## 1. What Has Been Built (✅ COMPLETE)

### A. Foundation Layer
| File | Source | Notes |
|------|--------|-------|
| [requirements.txt](file:///c:/Users/Saahil/Desktop/snack-overflow/requirements.txt) | Section 6.3.2 | All Python backend deps (FastAPI, SQLAlchemy, NumPy, SciPy, PyJWT, etc.) |
| [app/\_\_init\_\_.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/__init__.py) | — | Package init |
| [app/schemas.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/schemas.py) | **Verbatim** Section 5.3 | All Pydantic models, enums, envelopes with CamelModel and roundings |
| [app/core/\_\_init\_\_.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/core/__init__.py) | — | Package init |
| [app/core/config.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/core/config.py) | Section 6.3.6 | Env configuration: DATABASE_URL, JWT_SECRET, FRONTEND_BASE_URL, etc. |
| [app/core/errors.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/core/errors.py) | **Verbatim** Section 3.3 | ApiError, install_error_handling, CORS middleware with universal error envelope |
| [app/core/auth.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/core/auth.py) | **Verbatim** Section 3.4 | JWT issue/verify, CurrentUser, require_roles security dependency |

### B. Database Layer
| File | Source | Notes |
|------|--------|-------|
| [app/db/\_\_init\_\_.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/db/__init__.py) | — | Package init |
| [app/db/types.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/db/types.py) | **Verbatim** Section 5.4 | UTCDateTime, UUIDType, JSONType cross-database dialect types |
| [app/db/models.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/db/models.py) | Section 5.4 DDL | 11 ORM models matching schema.sql column-for-column with relationships |
| [app/db/session.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/db/session.py) | — | SQLite/PostgreSQL engine, SessionLocal, create_tables(), get_db() dependency |

### C. Service Layer (ALL 8 COMPLETE)
| File | PRD Section | Notes |
|------|-------------|-------|
| [app/services/\_\_init\_\_.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/__init__.py) | — | Package init |
| [app/services/weather.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/weather.py) | Section 4.3.3 | Open-Meteo API fetch, 30-min in-memory cache, rain simulation, weather summary |
| [app/services/dsp.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/dsp.py) | Section 4.3.4 | WAV header validation, bandpass filter, TAP/CHIRP pipelines, 13 MFCC features |
| [app/services/grading.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/grading.py) | Sections 4.3.4 steps 9–11, 4.3.6 | Stiffness, grade (A/B/C/REJECT), defect, rulFromCurve, requiredRouteTier |
| [app/services/pooling.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/pooling.py) | Section 4.3.6 | Haversine distance, 6 compatibility checks, match score calculation |
| [app/services/decay.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/decay.py) | Sections 4.3.7, 4.3.9 | Q10 dynamic decay factor, consumed hours calculation, shelf RUL |
| [app/services/markdown.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/markdown.py) | Section 4.3.9 | Shelf RUL threshold trigger, dynamic discount calculation, webhook payload |
| [app/services/disputes.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/disputes.py) | Section 4.3.10 | Telemetry checkpoint analysis, temp breach duration, carrier/farmer attribution |
| [app/services/pagination.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/pagination.py) | Section 6.3.7 | Cursor encode/decode `<createdAt ISO>|<id>` for standardized pagination |

### D. Router Layer (7 / 13 COMPLETE)
| File | PRD Section | Endpoints | Status |
|------|-------------|-----------|--------|
| [app/routers/\_\_init\_\_.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/__init__.py) | — | Package init | ✅ Complete |
| [app/routers/health.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/health.py) | 4.2 | `GET /health` | ✅ Complete |
| [app/routers/auth.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/auth.py) | 4.2 | `POST /auth/register`, `POST /auth/login` | ✅ Complete |
| [app/routers/users.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/users.py) | 4.2 | `GET /users/me`, `PATCH /users/me` | ✅ Complete |
| [app/routers/crop_profiles.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/crop_profiles.py) | 4.2 | `GET /crop-profiles`, `POST /crop-profiles`, `GET /crop-profiles/{id}`, `PUT /crop-profiles/{id}` | ✅ Complete |
| [app/routers/advisories.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/advisories.py) | 4.2, 4.3.3 | `POST /harvest-advisories`, `GET /harvest-advisories`, `GET /{id}`, `POST /{id}/override` | ✅ Complete |
| [app/routers/batches.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/batches.py) | 4.2 | `POST /batches`, `GET /batches`, `GET /batches/{id}` | ✅ Complete |
| [app/routers/passport.py](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/passport.py) | 4.2 | `GET /passport/{batchId}` (public Bio-Clock QR passport) | ✅ Complete |

---

## 2. What Still Needs to Be Built (❌ REMAINING)

### A. Routers Remaining (6 / 13)
| File | PRD Section | Routes & Purpose |
|------|-------------|------------------|
| `app/routers/assay.py` | 4.2, 4.3.4, 4.3.5 | `POST /assay/sonic-scans` (multipart WAV upload, idempotency, DSP processing, batch grading) |
| `app/routers/pools.py` | 4.2, 4.3.6, 4.3.7 | `GET/POST /pools`, `GET /pools/{id}`, `POST /pools/match`, `POST/DELETE /pools/{id}/reservations`, `POST /pools/{id}/dispatch`, `POST/GET /pools/{id}/telemetry`, `POST /pools/{id}/arrive` |
| `app/routers/listings.py` | 4.2, 4.3.8 | `GET/POST /listings`, `GET /listings/{id}`, `POST /listings/{id}/withdraw` |
| `app/routers/orders.py` | 4.2, 4.3.8 | `POST/GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/markdown-check` |
| `app/routers/intake.py` | 4.2, 4.3.9 | `POST /intake/verify` (buyer acoustic intake rescan, variance calculation, auto-dispute trigger) |
| `app/routers/disputes.py` | 4.2, 4.3.10 | `POST/GET /disputes`, `GET /disputes/{id}` |

### B. Application Entry Point & Seed Script
| File | PRD Section | What It Does |
|------|-------------|--------------|
| `app/main.py` | 6.3.4 | FastAPI app setup, CORS, error handling, router inclusion, startup seed trigger |
| `app/seed.py` | 6.4 | Seeds 4 users, 5 crop profiles, 3 pools when `SEED_DEMO=true` and DB is empty |

### C. Test Suite
| File | PRD Section | What It Tests |
|------|-------------|---------------|
| `tests/__init__.py` | — | Package init |
| `tests/conftest.py` | 6.3.9 | Fixtures: TestClient, role auth tokens, synthetic WAV audio generator, in-memory SQLite |
| `tests/test_health.py` | 6.5 step 1 | `GET /health` returns status ok and timestamp |
| `tests/test_auth.py` | 6.5 steps 2, 12 | Registration, login, duplicate phone handling, 401/403 checks |
| `tests/test_crop_profiles.py` | 6.5 step 3 | CRUD operations, admin-only write permission |
| `tests/test_advisories.py` | 6.5 step 4 | Weather-based advisory generation, farmer override |
| `tests/test_batches.py` | 6.5 step 5 | Batch creation, listing, scoping by farmer |
| `tests/test_assay.py` | 6.5 step 6, 6.3.9 | 400 Hz WAV upload, idempotency, rejection of corrupt/out-of-range frequencies |
| `tests/test_pools.py` | 6.5 steps 7, 9 | Pool matching, reservation, dispatch, telemetry logging, arrival |
| `tests/test_listings_orders.py` | 6.5 step 8 | Marketplace listing, order creation, reserve inventory |
| `tests/test_intake_disputes.py` | 6.5 steps 10, 11 | Buyer intake scan, markdown checks, dispute filing & attribution |
| `tests/test_errors.py` | 6.5 step 12 | Uniform error envelopes, 401/403/404/422 status codes, CORS headers |

---

## 3. Key PRD Rules to Follow

1. **Every route** must declare `response_model=ApiSuccess[<Type>]` and return `ApiSuccess(data=...)` — PRD Rule 9
2. **Status codes**: `201` for row-creating routes, `200` for everything else — Section 4.2
3. **Cursor pagination**: base64 of `"<createdAt ISO>|<id>"` — Section 6.3.7
4. **Rounding** per Rule 14 on response DTOs only (never stored values)
5. **camelCase JSON** everywhere via `CamelModel` with `serialize_by_alias=True`
6. **No trailing slashes**: `redirect_slashes=False` — Rule 4
7. **Visibility/ownership** scoping per Section 4.3.1 table
8. **State machines** per Section 4.3.2
9. **Seed on startup** when `SEED_DEMO=true` and `users` table is empty — Section 6.4
10. **Multipart scan route** must follow the exact signature from PRD Section 5.3:
    ```python
    @router.post("/sonic-scans", response_model=ApiSuccess[ScanResponse], status_code=201)
    async def create_sonic_scan(
        file: UploadFile = File(...),
        batch_id: UUID = Form(...),
        scan_type: ScanType = Form(...),
        device_model: str = Form(...),
        idempotency_key: UUID = Form(...),
        user: CurrentUser = Depends(require_roles("FARMER", "BUYER", "ADMIN")),
        db: Session = Depends(get_db),
    ) -> ApiSuccess[ScanResponse]:
    ```
11. **HarvestBatch computed fields**: `farmerName`, `cropName`, `ethyleneClass`, `poolId`, `qrCodeValue` — Section 5.1
12. **Listing computed fields**: `farmerName`, `cropProfileId`, `cropName`, `qualityGrade`, `internalDefectFlag`, `currentRulHours`, `routeTier`, `guaranteedArrivalRulHours`, `pickupLatitude`, `pickupLongitude` — Section 5.1
13. **TransportPool computed fields**: `carrierName`, `bookedCapacityKg`, `memberCount`, `ethyleneClasses` — Section 5.1
14. **PoolMember computed fields**: `farmerId`, `farmerName`, `cropName`, `ethyleneClass`, `currentRulHours` — Section 5.1
15. **Log markdown webhook payload at INFO level as JSON** — Section 6.3.10

---

## 4. Build Order for Remaining Work

```
1. app/routers/assay.py       <-- NEXT STEP
2. app/routers/pools.py
3. app/routers/listings.py
4. app/routers/orders.py
5. app/routers/intake.py
6. app/routers/disputes.py
7. app/main.py
8. app/seed.py
9. tests/conftest.py + all test files
10. Run pytest suite until 100% pass
```

---

## 5. Seed Data Reference (PRD Section 6.4)

**Users** (password: `Demo@12345` for all):
- **Ramesh Pawar**: `+919800000001`, `FARMER`, `HI`, "Pimpalgaon Tomato FPO", `(20.166700, 73.983300)`
- **Sunita Logistics**: `+919800000002`, `LOGISTICS`, `EN`, "Sahyadri Reefer Lines", `(20.011000, 73.790000)`
- **Arjun Mehta**: `+919800000003`, `BUYER`, `EN`, "Nashik Road Dark Store 4", `(19.954800, 73.837000)`
- **Dr. Kavita Rao**: `+919800000004`, `ADMIN`, `EN`, "FarmPool Agronomy", `(null, null)`

**5 Crop Profiles**: `TOMATO`, `MANGO`, `CUCUMBER`, `WATERMELON`, `POMEGRANATE` (calibration constants defined in PRD Section 6.4 table)

**3 Pools**: `FAST_QCOMM`, `FLEX_REGIONAL`, `STANDARD_WHOLESALE` (carrier = Sunita Logistics)
