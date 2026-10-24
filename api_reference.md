# FarmPool360 — Complete API Reference for Deployment

> [!IMPORTANT]
> **Framework:** FastAPI (Python) · **DB:** SQLite (default) · **Auth:** JWT (HS256, 24h TTL)
> **Base prefix:** All endpoints are under `/api/v1/`

---

## Environment Variables to Set

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./farmpool.db` | Switch to PostgreSQL for production |
| `JWT_SECRET` | `dev-only-change-me-at-least-32chars!` | **⚠️ MUST change for production** |
| `FRONTEND_BASE_URL` | `http://localhost:3000` | Used in QR code URLs |
| `CORS_EXTRA_ORIGINS` | `""` | Comma-separated extra CORS origins |
| `AUDIO_DIR` | `./data/audio` | Where WAV files are stored on disk |
| `SEED_DEMO` | `true` | Set `false` in production |
| `ENV` | `dev` | Set to `production` |

---

## External API Dependency

| Service | URL | Used By |
|---|---|---|
| **Open-Meteo** (weather forecast) | `https://api.open-meteo.com/v1/forecast` | [`weather.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/services/weather.py) → called from [`advisories.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/advisories.py) |

> **No API key required.** Open-Meteo is free/open. Responses are cached for 30 min.

---

## All Endpoints (38 total)

### 1. Health — [`health.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/health.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | ❌ None | Health check, returns contract version |

---

### 2. Auth — [`auth.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/auth.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | ❌ None | Register a new user |
| `POST` | `/api/v1/auth/login` | ❌ None | Login, returns JWT + user |

---

### 3. Users — [`users.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/users.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/users/me` | 🔒 Any role | Get current user's profile |
| `PATCH` | `/api/v1/users/me` | 🔒 Any role | Update current user's profile |

---

### 4. Crop Profiles — [`crop_profiles.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/crop_profiles.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/crop-profiles` | 🔒 Any role | List crop profiles (paginated, sorted by cropName) |
| `GET` | `/api/v1/crop-profiles/{crop_profile_id}` | 🔒 Any role | Get single crop profile |
| `POST` | `/api/v1/crop-profiles` | 🔒 **ADMIN** | Create crop profile |
| `PUT` | `/api/v1/crop-profiles/{crop_profile_id}` | 🔒 **ADMIN** | Update crop profile |

---

### 5. Harvest Advisories — [`advisories.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/advisories.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/harvest-advisories` | 🔒 **FARMER** | Create advisory (calls Open-Meteo) |
| `GET` | `/api/v1/harvest-advisories` | 🔒 **FARMER** | List own advisories (paginated) |
| `GET` | `/api/v1/harvest-advisories/{advisory_id}` | 🔒 FARMER / ADMIN | Get single advisory |
| `POST` | `/api/v1/harvest-advisories/{advisory_id}/override` | 🔒 FARMER (owner) / ADMIN | Override advisory recommendation |

---

### 6. Batches — [`batches.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/batches.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/batches` | 🔒 **FARMER** | Create harvest batch |
| `GET` | `/api/v1/batches` | 🔒 Any role (scoped) | List batches (paginated, role-scoped) |
| `GET` | `/api/v1/batches/{batch_id}` | 🔒 Any role (ownership check) | Get single batch |

---

### 7. Assay (SonicAssay) — [`assay.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/assay.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/assay/sonic-scans` | 🔒 FARMER / LOGISTICS / BUYER / ADMIN | Upload WAV audio, run DSP + grading. **Multipart form** (audio file + form fields) |

> [!NOTE]
> This endpoint accepts `multipart/form-data` with a WAV audio file (max 2 MB). Audio files are saved to `AUDIO_DIR`.

---

### 8. Pools — [`pools.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/pools.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/pools` | 🔒 **LOGISTICS** | Create transport pool |
| `GET` | `/api/v1/pools` | 🔒 Any role (scoped) | List pools (paginated, filterable) |
| `GET` | `/api/v1/pools/{pool_id}` | 🔒 Any role | Get pool detail with members |
| `POST` | `/api/v1/pools/match` | 🔒 **FARMER** | Match a batch to compatible pools |
| `POST` | `/api/v1/pools/{pool_id}/reservations` | 🔒 **FARMER** | Reserve a batch in a pool |
| `DELETE` | `/api/v1/pools/{pool_id}/reservations/{batch_id}` | 🔒 **FARMER** | Cancel reservation |
| `POST` | `/api/v1/pools/{pool_id}/dispatch` | 🔒 **LOGISTICS** (owner) | Dispatch pool (OPEN → IN_TRANSIT) |
| `POST` | `/api/v1/pools/{pool_id}/telemetry` | 🔒 **LOGISTICS** (owner) | Ingest temp/GPS reading, update RUL via Q10 decay |
| `GET` | `/api/v1/pools/{pool_id}/telemetry` | 🔒 Any role | List telemetry readings (paginated) |
| `POST` | `/api/v1/pools/{pool_id}/arrive` | 🔒 **LOGISTICS** (owner) | Mark pool as arrived |

---

### 9. Listings — [`listings.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/listings.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/listings` | 🔒 **FARMER** | Create marketplace listing |
| `GET` | `/api/v1/listings` | 🔒 Any role (scoped) | List listings (paginated, filterable) |
| `GET` | `/api/v1/listings/{listing_id}` | 🔒 Any role | Get single listing |
| `POST` | `/api/v1/listings/{listing_id}/withdraw` | 🔒 **FARMER** (owner) | Withdraw listing |

---

### 10. Orders — [`orders.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/orders.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/orders` | 🔒 **BUYER** | Place an order on a listing |
| `GET` | `/api/v1/orders` | 🔒 BUYER / FARMER / ADMIN | List orders (paginated, role-scoped) |
| `GET` | `/api/v1/orders/{order_id}` | 🔒 BUYER / FARMER / ADMIN | Get single order |
| `POST` | `/api/v1/orders/{order_id}/markdown-check` | 🔒 **BUYER** (owner) | Check/trigger markdown pricing |

---

### 11. Intake — [`intake.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/intake.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/intake/verify` | 🔒 **BUYER** | Verify intake scan against stiffness tolerance |

---

### 12. Disputes — [`disputes.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/disputes.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/disputes` | 🔒 BUYER / FARMER / ADMIN | File a dispute on an order |
| `GET` | `/api/v1/disputes` | 🔒 BUYER / FARMER / ADMIN | List disputes (paginated, role-scoped) |
| `GET` | `/api/v1/disputes/{dispute_id}` | 🔒 BUYER / FARMER / ADMIN | Get single dispute |

---

### 13. Passport (Public) — [`passport.py`](file:///c:/Users/Saahil/Desktop/snack-overflow/app/routers/passport.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/passport/{batch_id}` | ❌ None | Public bio-clock QR passport (batch + scans + pool + telemetry) |

---

## Project File Map

```
snack-overflow/
├── app/
│   ├── __init__.py              # App package
│   ├── schemas.py               # All Pydantic request/response models
│   ├── seed.py                  # Demo data seeder
│   ├── core/
│   │   ├── config.py            # Env vars (DATABASE_URL, JWT_SECRET, etc.)
│   │   ├── auth.py              # JWT issue/verify, CurrentUser, role guards
│   │   └── errors.py            # ApiError exception + handler
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models (all tables)
│   │   ├── session.py           # DB engine + session factory
│   │   └── types.py             # Custom SQLAlchemy column types
│   ├── routers/                 # ← ALL API ENDPOINTS LIVE HERE
│   │   ├── health.py            # 1 endpoint
│   │   ├── auth.py              # 2 endpoints
│   │   ├── users.py             # 2 endpoints
│   │   ├── crop_profiles.py     # 4 endpoints
│   │   ├── advisories.py        # 4 endpoints
│   │   ├── batches.py           # 3 endpoints
│   │   ├── assay.py             # 1 endpoint (multipart upload)
│   │   ├── pools.py             # 10 endpoints
│   │   ├── listings.py          # 4 endpoints
│   │   ├── orders.py            # 4 endpoints
│   │   ├── intake.py            # 1 endpoint
│   │   ├── disputes.py          # 3 endpoints
│   │   └── passport.py          # 1 endpoint
│   └── services/                # Business logic (no endpoints)
│       ├── decay.py             # Q10 decay math
│       ├── disputes.py          # Dispute segment builder
│       ├── dsp.py               # Audio DSP (tap/chirp processing)
│       ├── grading.py           # Quality grading, RUL, route tier
│       ├── markdown.py          # Markdown pricing logic
│       ├── pagination.py        # Cursor-based pagination helper
│       ├── pooling.py           # Pool compatibility + scoring
│       └── weather.py           # Open-Meteo fetcher (external API)
├── requirements.txt             # Python dependencies
└── farmpool.db                  # SQLite database (dev)
```

---

## Deployment Checklist

> [!WARNING]
> Before deploying, make sure to:

- [ ] **Set `JWT_SECRET`** to a strong random 32+ char string
- [ ] **Set `DATABASE_URL`** to a production database (e.g. PostgreSQL)
- [ ] **Set `SEED_DEMO=false`** to skip demo data seeding
- [ ] **Set `ENV=production`**
- [ ] **Set `FRONTEND_BASE_URL`** to your actual frontend URL
- [ ] **Set `AUDIO_DIR`** to a persistent volume path (audio files are stored here)
- [ ] **Set `CORS_EXTRA_ORIGINS`** if your frontend runs on a different domain
- [ ] Ensure the server can reach `https://api.open-meteo.com` (the only external API)
