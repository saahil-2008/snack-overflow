# FarmPool 360 × ChronoCrop — Implementation PRD & API Contract

**Version:** 1.1.0 (contract-locked) · **Date:** 2026-10-24 · **Owner:** Chris Alex · **Status:** Ready for build
**Stack:** Next.js 14+ App Router (frontend, built with v0) · FastAPI + Pydantic v2 (backend, built with Claude Code) · PostgreSQL 15 (prod) / SQLite (demo)
**Supersedes:** PRD v1.0 (`PRD_FarmPool_360___ChronoCrop.docx`). Product rationale, science notes, business model, roadmap and demo script from v1.0 remain valid; this document is the **build contract** and wins on any conflict.

> **How to use this file.** Give the *whole* file to both AIs. The frontend copies Section 5.2 verbatim to `lib/api/types.ts` and Section 6.2's client to `lib/api/client.ts`. The backend copies Section 5.3 verbatim to `app/schemas.py`, Section 3.3 to `app/core/errors.py`, Section 3.4 to `app/core/auth.py` and Section 5.4 to the database layer. Neither side may add, rename or drop a route, field or enum value. If one side needs a change, edit this document first, bump the version, and re-share it with both.

---

## 1. APP OVERVIEW & USER FLOWS

### 1.1 Product summary

FarmPool 360 × ChronoCrop is a three-sided platform (farmers/FPOs, logistics partners, buyers) that:

1. **HarvestWindow** — tells a farmer *when to harvest* from manual crop inputs plus a 72-hour Open-Meteo forecast: `HARVEST_NOW`, `RECHECK_TOMORROW` or `WAIT_48H`, with confidence, explanation and manual override.
2. **SonicAssay** — measures internal firmness from a smartphone acoustic scan (3-tap impulse, optional chirp): peak frequency f0, damping τ, Cooke stiffness index **S = f0² · m^(2/3)**, grade A/B/C, internal-defect flag and initial remaining useful life (RUL, hours).
3. **Bio-Clock QR Passport** — one QR per batch; a public page showing the append-only scan and temperature history.
4. **FarmPool** — stock ledger, pool reservation, compatibility matching (≤ 20 km, ethylene class, RUL ± 24 h), FEFT routing tiers, transit telemetry with Q10 decay.
5. **Marketplace & dark-store intake** — listings with guaranteed arrival RUL, intake spot-check vs dispatch stiffness, flash markdown when shelf RUL < 24 h, dispute ledger attributing RUL loss to farm, transit or buyer storage.

**Out of scope (no fields, no endpoints):** computer vision (no image upload, no crop recognition, no mass estimation), Pheno-Sow sowing planner, real payments or settlement, milk / sealed-pack testing.

**Platform:** UI in English, Hindi, Marathi, Tamil · dark mode · installable PWA with an offline scan queue.

### 1.2 Target audience and roles

| Role (`Role`) | Who | Core need | Self-register? |
|---|---|---|---|
| `FARMER` | Smallholder farmer or FPO grader | Harvest timing, fair non-destructive grading, cheap shared transport | Yes |
| `LOGISTICS` | 3PL carrier / truck operator | Fuller trucks, clear pickup windows, spoilage-proof routing | Yes |
| `BUYER` | Wholesaler or quick-commerce dark-store manager | Verified quality, guaranteed arrival shelf life, simple intake | Yes |
| `ADMIN` | Internal agronomist | Maintain crop calibration profiles | No (seeded only) |

### 1.3 Screen map (frontend routes → endpoints)

Every frontend route below may call **only** the endpoints listed for it. Paths are relative to `/api/v1`.

| Frontend route | Roles | Purpose | Endpoints used |
|---|---|---|---|
| `/login`, `/register` | public | Auth | `POST /auth/login`, `POST /auth/register` |
| `/settings` | all | Language, theme, profile, home location | `GET /users/me`, `PATCH /users/me` |
| `/passport/[batchId]` | public | Bio-Clock QR page | `GET /passport/{batchId}` |
| `/farmer` | FARMER | Dashboard: latest advisory, stock summary | `GET /harvest-advisories`, `GET /batches` |
| `/farmer/harvest-window` | FARMER | Advisory form, action card, override | `GET /crop-profiles`, `POST /harvest-advisories`, `POST /harvest-advisories/{advisoryId}/override` |
| `/farmer/batches` | FARMER | Stock ledger | `GET /batches` |
| `/farmer/batches/new` | FARMER | Create batch after harvest | `GET /crop-profiles`, `POST /batches` |
| `/farmer/batches/[batchId]` | FARMER | Batch detail, QR, scan, pool, list | `GET /batches/{batchId}`, `GET /passport/{batchId}`, `POST /assay/sonic-scans`, `POST /pools/match`, `POST /pools/{poolId}/reservations`, `DELETE /pools/{poolId}/reservations/{batchId}`, `POST /listings` |
| `/farmer/listings` | FARMER | My listings | `GET /listings?mine=true`, `POST /listings/{listingId}/withdraw` |
| `/farmer/orders` | FARMER | Orders placed on my batches, disputes | `GET /orders`, `GET /orders/{orderId}`, `POST /disputes`, `GET /disputes`, `GET /disputes/{disputeId}` |
| `/logistics` | LOGISTICS | Pool board | `GET /pools?mine=true` |
| `/logistics/pools/new` | LOGISTICS | Create pool | `POST /pools` |
| `/logistics/pools/[poolId]` | LOGISTICS | Members, capacity bar, loading scan, dispatch, telemetry, arrive | `GET /pools/{poolId}`, `POST /assay/sonic-scans`, `POST /pools/{poolId}/dispatch`, `POST /pools/{poolId}/telemetry`, `GET /pools/{poolId}/telemetry`, `POST /pools/{poolId}/arrive` |
| `/buyer/marketplace` | BUYER | Browse and filter listings, order | `GET /crop-profiles`, `GET /listings`, `GET /listings/{listingId}`, `POST /orders` |
| `/buyer/orders` | BUYER | My orders | `GET /orders` |
| `/buyer/orders/[orderId]` | BUYER | Intake scan, verify, markdown, dispute | `GET /orders/{orderId}`, `GET /passport/{batchId}`, `POST /assay/sonic-scans`, `POST /intake/verify`, `POST /orders/{orderId}/markdown-check`, `POST /disputes` |
| `/buyer/disputes/[disputeId]` | BUYER | Attribution report | `GET /disputes/{disputeId}` |
| `/admin/crop-profiles` | ADMIN | Calibration console | `GET /crop-profiles`, `GET /crop-profiles/{cropProfileId}`, `POST /crop-profiles`, `PUT /crop-profiles/{cropProfileId}` |
| (app boot) | all | Backend reachability badge | `GET /health` |

### 1.4 Primary user journeys

**Farmer (FPO grader)**
1. Registers with phone + password, role `FARMER`, language `HI` → `POST /auth/register` → token stored, UI switches to Hindi.
2. Opens HarvestWindow, picks crop (from `GET /crop-profiles`), enters days since flowering and target pickup date; location comes from GPS or profile → `POST /harvest-advisories`.
3. Sees the action card (e.g. `RECHECK_TOMORROW`, 65 %). Toggles "simulate rain in 30 h" (`simulateRainInHours: 30`) → card flips to `HARVEST_NOW`. Optionally overrides with a reason → `POST /harvest-advisories/{advisoryId}/override`.
4. After picking, creates a batch (crop, total kg, average fruit mass g, pickup point, linked advisory) → `POST /batches` → status `PENDING_ASSAY`, QR shown.
5. Runs SonicAssay on 1–3 sample fruits: 1.5 s of silence, then 3 taps on the equator; the app shows a live spectrogram and uploads a WAV per fruit → `POST /assay/sonic-scans` (`stage: FARM_GATE`). Batch becomes `GRADED` with grade, defect flag and RUL.
6. Taps "Find a pool" → `POST /pools/match` → picks the top match → `POST /pools/{poolId}/reservations` → batch `POOLED`.
7. Lists the batch for sale with a price per kg → `POST /listings`.
8. **Outcome:** a graded, pooled, listed batch with a public QR passport; later sees orders and any dispute attribution on `/farmer/orders`.

**Logistics partner**
1. Registers with role `LOGISTICS`.
2. Creates a pool: route tier, origin cluster, destination, capacity, pickup window → `POST /pools`.
3. Watches the capacity bar fill on the pool board → `GET /pools?mine=true`, `GET /pools/{poolId}`.
4. At loading, optionally re-scans each batch → `POST /assay/sonic-scans` (`stage: LOADING`).
5. Dispatches → `POST /pools/{poolId}/dispatch` → pool and batches `IN_TRANSIT`.
6. Sends temperature readings (live or with the demo simulator) → `POST /pools/{poolId}/telemetry` → sees each batch's RUL drop and any reroute suggestion.
7. Marks arrival → `POST /pools/{poolId}/arrive`.
8. **Outcome:** a delivered pool with a complete temperature log attached to every batch passport.

**Buyer (dark-store manager)**
1. Registers with role `BUYER` and an organization name.
2. Browses listings filtered by crop, grade and minimum guaranteed arrival RUL → `GET /listings`.
3. Orders a quantity → `POST /orders` → order `PLACED`.
4. On arrival, scans the crate QR (opens `/passport/{batchId}`), runs a 1-fruit acoustic spot-check → `POST /assay/sonic-scans` (`stage: INTAKE`), then verifies → `POST /intake/verify` with storage temperature → `INTAKE_ACCEPTED` or `INTAKE_FLAGGED`.
5. Checks shelf life (demo: fast-forward hours) → `POST /orders/{orderId}/markdown-check` → if shelf RUL < 24 h a flash markdown fires (simulated webhook payload shown).
6. If unhappy, raises a dispute → `POST /disputes` → sees loss attributed to `FARM`, `TRANSIT`, `BUYER_STORAGE` or `NONE`.
7. **Outcome:** stock accepted without cutting fruit, markdown applied before spoilage, evidence-based dispute record.

**Admin (agronomist)**
1. Logs in with the seeded admin account → edits a crop's grade thresholds, RUL curve or Q10 → `PUT /crop-profiles/{cropProfileId}`.
2. **Outcome:** new scans and advisories use the updated calibration immediately (existing scans are never recomputed).


---

## 2. GLOBAL SYSTEM RULES

**Transport and URLs**
1. Serve every route under the prefix `/api/v1`. Backend runs on `http://localhost:8000`; frontend on `http://localhost:3000` and reads `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).
2. Use `Content-Type: application/json` for every request body except `POST /api/v1/assay/sonic-scans` (multipart, Rule 22). Routes documented with "no body" receive no body; the backend ignores any body sent to them.
3. Use exactly the HTTP method and success status in Section 4.2: `201` for routes that create a row, `200` for everything else. Never return `204`; every 2xx carries the success envelope.
4. Do not add trailing slashes. `GET /api/v1/pools` is valid, `GET /api/v1/pools/` is not (FastAPI: `redirect_slashes=False`).

**JSON shape**
5. All request and response keys are **camelCase**, including keys nested inside JSON columns (`rulCurve`, `segments`, `displayName`) and query-string parameters (`?minArrivalRulHours=48`).
6. Backend: every schema inherits the shared base model in Section 5.3:
   `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, from_attributes=True, extra="forbid")`.
   Requests are parsed by alias, responses are emitted by alias (`response_model_by_alias` stays at its default `True`). `extra="forbid"` makes unknown request keys a `VALIDATION_ERROR`, which is how invented fields get caught.
7. **Never put a letter directly after a digit inside one snake_case segment** (`next_48h`, `f0s`): `to_camel` would emit `Next48H` / `F0S`. Use `f0_hz`, `tap_f0_values_hz` style names. Every field in Section 5 already obeys this.
8. Because of `serialize_by_alias=True`, `model.model_dump()` returns camelCase keys. When copying request data onto ORM objects use `model.model_dump(by_alias=False, exclude_unset=True)`.
9. Success envelope for every 2xx: `{ "success": true, "data": <payload> }`. Backend wraps with `ApiSuccess[T]`; frontend unwraps in one place (`lib/api/client.ts`).
10. List endpoints return `data: { "items": T[], "nextCursor": string | null }`. Query params: `limit` (integer 1–100, default 20) and `cursor` (opaque string from a previous `nextCursor`). Default sort is `createdAt` descending then `id` descending; telemetry lists sort by `recordedAt` ascending. `nextCursor` is `null` on the last page. Arrays embedded inside an object (`members`, `scans`, `segments`) are never paginated.

**Types and values**
11. **IDs:** every entity id (including batch / QR ids) is a UUID v4 string, lowercase with hyphens, generated by the backend with `uuid.uuid4()`. The only client-generated UUID is `clientScanId` (`crypto.randomUUID()`).
12. **Datetimes:** ISO 8601 UTC with seconds precision and trailing `Z`, e.g. `2026-10-24T12:00:00Z`. Backend uses timezone-aware UTC datetimes only (`datetime.now(timezone.utc)`), rejects naive input (`VALIDATION_ERROR`, type `timezone_aware`), converts offset input (`+05:30`) to UTC, and serialises through the `UtcDateTime` type in Section 5.3. Frontend sends `new Date().toISOString().replace(/\.\d{3}Z$/, "Z")` and displays in the user's local time zone (Asia/Kolkata for the demo).
13. **Units are in the field name** wherever ambiguous: `Kg`, `G` (grams), `Hours`, `Hz`, `Ms` (milliseconds), `C` (°C), `Pct` (0–100), `Kpa`, `Km`, `Inr` (rupees). `confidence`, `maturityFraction` and `score` are 0–1 fractions. `stiffnessIndex` is Hz²·g^(2/3) (arbitrary, crop-relative units).
14. **Rounding (output only; store full precision):** hours, Hz, °C, %, km → 1 decimal · `tauMs` → 2 decimals · kg and INR → 2 decimals · `stiffnessIndex` → 0 decimals · `confidence`, `maturityFraction` → 2 decimals · `score`, `decayFactor` → 3 decimals · coordinates → 6 decimals. `mfccMean` values → 3 decimals.
15. **Enums:** defined once in Section 5 with UPPER_SNAKE string values, identical in TypeScript (`as const` arrays), Python (`StrEnum` with name == value) and SQL (`CHECK (... IN (...))`). Use them verbatim; never translate or lowercase enum values on the wire. The UI translates enum values to labels via i18n dictionaries keyed by the enum value.
16. **Nullability:** a field typed `T | null` in TypeScript is `T | None` without a default in Pydantic: the key is **always present** (send `null` explicitly; omission is a `VALIDATION_ERROR`). The only omittable keys are those marked `?` in TypeScript: `UpdateProfileRequest` (PATCH), optional multipart fields, and query params.
17. Booleans are JSON `true`/`false`; query-string booleans are `true`/`false` literals.
18. Numbers are JSON numbers, never strings (multipart form values are the only exception, Rule 22).

**Auth**
19. **Register / login:** `POST /api/v1/auth/register` and `POST /api/v1/auth/login` return `AuthResponse { accessToken, tokenType: "Bearer", expiresAt, user }`. Passwords are hashed with bcrypt (passlib or `bcrypt` package). `ADMIN` cannot self-register.
20. **Token:** JWT, HS256, secret from env `JWT_SECRET` (≥ 32 chars), lifetime 24 h, no refresh token (log in again). Claims: `sub` (userId), `userId` (UUID string), `role` (`Role`), `iat`, `exp` (Unix seconds). Sent as `Authorization: Bearer <token>`. Frontend stores it in `localStorage` key `fp_access_token`.
21. **401 vs 403:** `401` when the token is missing (`AUTH_REQUIRED`), malformed or bad signature (`TOKEN_INVALID`), expired (`TOKEN_EXPIRED`), or credentials are wrong (`INVALID_CREDENTIALS`). `403 FORBIDDEN_ROLE` when the token is valid but the role is not in the route's Auth/Role column. `403 NOT_OWNER` when the role is allowed but the resource belongs to someone else (e.g. a farmer reading another farmer's batch). Frontend: on any 401 clear the token and redirect to `/login?next=<current path>`; on 403 show a "not allowed" toast and stay on the page.

**Multipart exception**
22. `POST /api/v1/assay/sonic-scans` is `multipart/form-data` with exactly these parts (camelCase names, string values):

| Part | Required | Value |
|---|---|---|
| `audio` | yes | File, filename `scan.wav`, content type `audio/wav`; RIFF PCM 16-bit, mono, 44 100 or 48 000 Hz, 3–15 s long, ≤ 2 MB. First 1.5 s must be ambient silence. |
| `batchId` | yes | UUID |
| `stage` | yes | `FARM_GATE` \| `LOADING` \| `INTAKE` |
| `mode` | yes | `TAP` \| `CHIRP` |
| `clientScanId` | yes | UUID generated on the device (idempotency key) |
| `recordedAt` | yes | ISO 8601 UTC with `Z` (time the recording started on the device) |
| `phoneModel` | no | ≤ 80 chars, e.g. `navigator.userAgentData?.model`; omit the part if unknown |
| `avgFruitMassG` | no | decimal string > 0 and ≤ 20000; omit to use the batch's `avgFruitMassG` |

Optional parts are **omitted**, never sent as the string `"null"`. Do not set the `Content-Type` header manually (the browser adds the boundary). MediaRecorder output (webm/opus, mp4/aac) is **not** accepted: capture raw samples with an AudioWorklet and encode WAV (encoder in Section 6.2).

**Operational**
23. CORS allows exactly `http://localhost:3000`, `http://127.0.0.1:3000` plus any comma-separated origins in env `CORS_EXTRA_ORIGINS` (for a deployed demo), methods `GET, POST, PUT, PATCH, DELETE, OPTIONS`, headers `Authorization, Content-Type`, `allow_credentials=False` (tokens travel in a header, not cookies).
24. All business timestamps (`createdAt`, `rulUpdatedAt`, …) are set by the server clock, except `recordedAt` on scans (device time) and telemetry (`recordedAt` may be supplied for simulation).
25. `acoustic_scans` and `telemetry_readings` are append-only: no update or delete route exists and the service layer never issues `UPDATE`/`DELETE` on them.
26. Language affects only the UI. The backend never localises text; `explanation` and error `message` are English, and the UI renders localized copy from enum codes (`reasonCode`, `error.code`).


---

## 3. UNIVERSAL ERROR FORMAT

### 3.1 Shape

Every 4xx and 5xx response body is exactly:

```json
{ "success": false, "error": { "code": "ERROR_CODE_STRING", "message": "Human readable message", "details": {} } }
```

`code` is an `ErrorCode` value (Section 5). `message` is English and safe to show as a fallback; the UI shows a localized string keyed by `code` when it has one. `details` is always an object (empty `{}` when there is nothing to add). Example validation error:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": { "fields": [ { "field": "pickupLatitude", "message": "Input should be less than or equal to 90", "type": "less_than_equal" } ] }
  }
}
```

### 3.2 Error codes

| Code | HTTP | When | `details` keys |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | Body, query, path or form fails schema validation (incl. unknown keys, naive datetimes, bad enum) | `fields: ValidationFieldError[]` |
| `AUTH_REQUIRED` | 401 | No `Authorization: Bearer` header on a protected route | — |
| `TOKEN_INVALID` | 401 | Malformed token or bad signature | — |
| `TOKEN_EXPIRED` | 401 | `exp` in the past | — |
| `INVALID_CREDENTIALS` | 401 | Login phone/password mismatch | — |
| `FORBIDDEN_ROLE` | 403 | Valid token, role not allowed for the route | `requiredRoles: Role[]`, `yourRole: Role` |
| `NOT_OWNER` | 403 | Role allowed but resource belongs to another user / pool / order | `resource: string`, `id: UUID` |
| `NOT_FOUND` | 404 | Unknown route or entity id | `resource: string`, `id: string` (absent for unknown routes) |
| `METHOD_NOT_ALLOWED` | 405 | Wrong HTTP method on a known path | — |
| `PHONE_ALREADY_REGISTERED` | 409 | Register with an existing phone | `phone: string` |
| `BATCH_STATE_INVALID` | 409 | Batch status does not allow the action | `batchId`, `currentStatus: BatchStatus`, `allowedStatuses: BatchStatus[]` |
| `POOL_STATE_INVALID` | 409 | Pool status does not allow the action (or dispatching an empty pool) | `poolId`, `currentStatus: PoolStatus`, `allowedStatuses: PoolStatus[]`, `reason: string` |
| `POOL_INCOMPATIBLE` | 409 | Reservation fails a compatibility rule | `poolId`, `reasons: CompatibilityReason[]` |
| `LISTING_UNAVAILABLE` | 409 | Listing not `ACTIVE`, quantity above `availableKg`, or a second active listing for one batch | `listingId: UUID \| null`, `availableKg: number`, `status: ListingStatus \| null` |
| `SCAN_MISMATCH` | 422 | `scanId` in intake verify is not an `INTAKE` scan of the order's batch by this buyer | `scanId`, `expectedBatchId`, `expectedStage: "INTAKE"` |
| `INTAKE_NOT_VERIFIED` | 409 | Markdown check or dispute before intake verify | `orderId` |
| `INTAKE_ALREADY_VERIFIED` | 409 | Second intake verify for one order | `orderId`, `intakeVerifiedAt` |
| `DISPUTE_ALREADY_EXISTS` | 409 | Second dispute for one order | `orderId`, `disputeId` |
| `TELEMETRY_OUT_OF_ORDER` | 409 | `recordedAt` not later than the previous reading (or before `dispatchedAt`) | `poolId`, `lastRecordedAt` |
| `AUDIO_TOO_LARGE` | 413 | Audio part > 2 MB | `maxBytes`, `receivedBytes` |
| `AUDIO_FORMAT_UNSUPPORTED` | 415 | Not RIFF PCM 16-bit WAV, wrong content type, stereo, sample rate not 44 100/48 000, or duration outside 3–15 s | `receivedContentType: string \| null`, `reason: string` |
| `IMPACTS_NOT_DETECTED` | 422 | TAP mode found fewer than 3 impacts (or CHIRP found no resonance peak) | `impactsFound: number`, `required: number` |
| `SCAN_REJECTED_TAP_VARIATION` | 422 | Coefficient of variation of the 3 tap f0 values > 12 % | `tapF0ValuesHz: number[]`, `tapVariationPct: number`, `maxAllowedPct: 12` |
| `WEATHER_UNAVAILABLE` | 502 | Open-Meteo unreachable / timed out (5 s) and `simulateRainInHours` is null | `provider: "OPEN_METEO"` |
| `INTERNAL_ERROR` | 500 | Any unhandled exception | — |

UI behaviour: `VALIDATION_ERROR` → show each `fields[].message` under the matching form input (match on `field`); `SCAN_REJECTED_TAP_VARIATION` / `IMPACTS_NOT_DETECTED` → "Please tap again" screen, no toast; `5xx` → retry toast.

### 3.3 Required FastAPI error wiring (`app/core/errors.py`)

Raise `ApiError(status, code, message, details)` for every contract error; never raise bare `HTTPException`. Call `install_error_handling(app, origins)` **after** creating the app and including routers. The catch-all is an HTTP middleware registered before `CORSMiddleware` so that even 500 responses carry CORS headers (a plain `@app.exception_handler(Exception)` runs outside CORS and the browser would report a CORS failure instead of the 500 envelope).

```python
# app/core/errors.py — Universal Error Format wiring (required, copy as-is)
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("farmpool")

_STATUS_TO_CODE = {401: "AUTH_REQUIRED", 403: "FORBIDDEN_ROLE", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
                   413: "AUDIO_TOO_LARGE", 415: "AUDIO_FORMAT_UNSUPPORTED", 422: "VALIDATION_ERROR"}


class ApiError(Exception):
    """Raise this from any route/service for a contract error."""

    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code, self.code, self.message, self.details = status_code, code, message, details or {}


def error_json(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code,
                        content={"success": False, "error": {"code": code, "message": message, "details": details or {}}})


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "form", "header")]
    return ".".join(parts) or "body"


def install_error_handling(app: FastAPI, cors_origins: list[str]) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_json(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "INTERNAL_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else code
        return error_json(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [{"field": _field_path(tuple(e.get("loc", ()))), "message": e.get("msg", "Invalid value"),
                   "type": e.get("type", "value_error")} for e in exc.errors()]
        return error_json(422, "VALIDATION_ERROR", "Request validation failed", {"fields": fields})

    # Catch-all as an HTTP middleware added BEFORE CORSMiddleware, so CORS stays the outer layer
    # and even 500 responses carry Access-Control-Allow-Origin (a plain Exception handler would not).
    @app.middleware("http")
    async def _catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:  # noqa: BLE001
            log.exception("Unhandled error on %s %s", request.method, request.url.path)
            return error_json(500, "INTERNAL_ERROR", "Something went wrong. Please retry.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
```

### 3.4 Required auth dependency (`app/core/auth.py`)

`HTTPBearer(auto_error=False)` is mandatory: with `auto_error=True` some FastAPI versions return `403 {"detail": "Not authenticated"}` for a missing header, which breaks Rule 21 and the envelope.

```python
# app/core/auth.py — JWT auth + role guard (required, copy as-is; uses PyJWT)
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ApiError

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL = timedelta(hours=24)
_bearer = HTTPBearer(auto_error=False)  # auto_error=False: we emit our own 401 envelope


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    role: str


def issue_token(user_id: UUID, role: str) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    exp = now + JWT_TTL
    claims = {"sub": str(user_id), "userId": str(user_id), "role": role, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM), exp


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise ApiError(401, "AUTH_REQUIRED", "Login required")
    try:
        claims = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return CurrentUser(user_id=UUID(claims["userId"]), role=claims["role"])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "TOKEN_EXPIRED", "Session expired, please log in again")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise ApiError(401, "TOKEN_INVALID", "Invalid token")


def require_roles(*roles: str):
    def _dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN_ROLE", "Your role cannot perform this action",
                           {"requiredRoles": list(roles), "yourRole": user.role})
        return user
    return _dep
```

Usage: `user: CurrentUser = Depends(require_roles("FARMER"))`; public routes have no auth dependency; "any" routes use `Depends(current_user)`.


---

## 4. API ENDPOINT CONTRACT

### 4.1 Conventions for the table

- Every route is prefixed `/api/v1`. Path params are UUIDs; a malformed UUID is `VALIDATION_ERROR`, an unknown one is `NOT_FOUND`.
- **Auth/Role:** `public` = no token; `any` = any authenticated role; otherwise only the listed roles (`FORBIDDEN_ROLE` for others). "owner" adds a `NOT_OWNER` check (Section 4.3.1).
- **Request Payload:** the named type is defined in Section 5; keys are listed with types for quick reading. `none` = send no body. `query:` lists optional query params.
- **Success Response:** HTTP status, then the type inside `data` of the success envelope `{ "success": true, "data": <payload> }`.
- This table is mirrored 1:1 by the `ApiRoutes` map in Section 5.2. No route exists outside it.

### 4.2 Endpoint table

| Feature | HTTP Method | Route (`/api/v1/<path>`) | Auth/Role | Request Payload (camelCase keys, with types) | Success Response Shape |
|---|---|---|---|---|---|
| Health | `GET` | `/api/v1/health` | public | none | 200 `HealthStatus` {status: "OK", version: string} |
| Auth: register | `POST` | `/api/v1/auth/register` | public | `RegisterRequest` {name: string, phone: string, password: string, role: "FARMER" \| "LOGISTICS" \| "BUYER", language: Language, organizationName: string \| null} | 201 `AuthResponse` {accessToken: string, tokenType: "Bearer", expiresAt: IsoDateTime, user: User} |
| Auth: login | `POST` | `/api/v1/auth/login` | public | `LoginRequest` {phone: string, password: string} | 200 `AuthResponse` |
| Profile | `GET` | `/api/v1/users/me` | any | none | 200 `User` |
| Profile & language/theme settings | `PATCH` | `/api/v1/users/me` | any | `UpdateProfileRequest` {name?: string, language?: Language, theme?: Theme, organizationName?: string \| null, homeLatitude?: number \| null, homeLongitude?: number \| null} | 200 `User` |
| Crop profiles: list | `GET` | `/api/v1/crop-profiles` | any | query: limit?: number, cursor?: string | 200 `Paginated<CropProfile>` (sorted by cropName ascending) |
| Crop profiles: get | `GET` | `/api/v1/crop-profiles/{cropProfileId}` | any | none | 200 `CropProfile` |
| Crop profiles: create | `POST` | `/api/v1/crop-profiles` | ADMIN | `CropProfileUpsertRequest` {cropName: string, displayName: LocalizedText, ethyleneClass: EthyleneClass, harvestWindowDaysMin: number, harvestWindowDaysMax: number, heatStressTempC: number, typicalFruitMassGMin: number, typicalFruitMassGMax: number, stiffnessGradeAMin: number, stiffnessGradeBMin: number, defectF0MaxHz: number, defectTauMaxMs: number, rulCurve: RulCurvePoint[], q10: number, referenceTempC: number, intakeStiffnessTolerancePct: number, markdownThresholdHours: number, defaultMarkdownPct: number, disputeToleranceHours: number, calibrationNote: string} | 201 `CropProfile` |
| Crop profiles: update | `PUT` | `/api/v1/crop-profiles/{cropProfileId}` | ADMIN | `CropProfileUpsertRequest` (full replace, same keys as create) | 200 `CropProfile` |
| HarvestWindow: advisory | `POST` | `/api/v1/harvest-advisories` | FARMER | `HarvestAdvisoryRequest` {cropProfileId: UUID, daysSinceFlowering: number (int), targetPickupDate: IsoDateTime, latitude: number, longitude: number, simulateRainInHours: number (int 0–47) \| null} | 201 `HarvestAdvisory` |
| HarvestWindow: history | `GET` | `/api/v1/harvest-advisories` | FARMER (own) | query: limit?: number, cursor?: string | 200 `Paginated<HarvestAdvisory>` |
| HarvestWindow: get | `GET` | `/api/v1/harvest-advisories/{advisoryId}` | FARMER owner, ADMIN | none | 200 `HarvestAdvisory` |
| HarvestWindow: manual override | `POST` | `/api/v1/harvest-advisories/{advisoryId}/override` | FARMER owner, ADMIN | `AdvisoryOverrideRequest` {overrideRecommendation: Recommendation, overrideReason: string} | 200 `HarvestAdvisory` |
| Batch: create (after harvest) | `POST` | `/api/v1/batches` | FARMER | `CreateBatchRequest` {cropProfileId: UUID, weightKg: number, avgFruitMassG: number, harvestedAt: IsoDateTime, pickupLatitude: number, pickupLongitude: number, harvestAdvisoryId: UUID \| null} | 201 `HarvestBatch` (status `PENDING_ASSAY`) |
| Stock ledger | `GET` | `/api/v1/batches` | any (scoped, 4.3.1) | query: status?: BatchStatus, limit?: number, cursor?: string | 200 `Paginated<HarvestBatch>` |
| Batch: get | `GET` | `/api/v1/batches/{batchId}` | any (scoped, 4.3.1) | none | 200 `HarvestBatch` |
| Bio-Clock QR passport | `GET` | `/api/v1/passport/{batchId}` | public | none | 200 `BatchPassport` {batch: HarvestBatch, scans: AcousticScan[], pool: TransportPool \| null, telemetry: TelemetryReading[]} |
| SonicAssay: acoustic scan | `POST` | `/api/v1/assay/sonic-scans` | FARMER (FARM_GATE), LOGISTICS (LOADING), BUYER (INTAKE) — see 4.3.5 | **multipart/form-data** `SonicScanFormFields` {audio: File (WAV), batchId: UUID, stage: ScanStage, mode: ScanMode, clientScanId: UUID, recordedAt: IsoDateTime, phoneModel?: string, avgFruitMassG?: string} | 201 `SonicScanResult` {scan: AcousticScan, batch: HarvestBatch}; 200 with the stored result when `clientScanId` was already processed |
| Pools: list | `GET` | `/api/v1/pools` | any | query: status?: PoolStatus, routeTier?: RouteTier, mine?: boolean, limit?: number, cursor?: string | 200 `Paginated<TransportPool>` |
| Pools: create | `POST` | `/api/v1/pools` | LOGISTICS | `CreatePoolRequest` {routeTier: RouteTier, originLabel: string, originLatitude: number, originLongitude: number, destinationName: string, destinationLatitude: number, destinationLongitude: number, maxCapacityKg: number, pickupWindowStart: IsoDateTime, pickupWindowEnd: IsoDateTime} | 201 `TransportPoolDetail` (status `OPEN`, members []) |
| Pools: get | `GET` | `/api/v1/pools/{poolId}` | any | none | 200 `TransportPoolDetail` |
| Pools: compatibility matching | `POST` | `/api/v1/pools/match` | FARMER (batch owner) | `PoolMatchRequest` {batchId: UUID} | 200 `PoolMatchResult` {batchId: UUID, batchRulHours: number, requiredRouteTier: RouteTier, matches: PoolMatch[], rejected: PoolRejection[]} |
| Pools: reserve space | `POST` | `/api/v1/pools/{poolId}/reservations` | FARMER (batch owner) | `CreateReservationRequest` {batchId: UUID} | 201 `PoolMember` |
| Pools: cancel reservation | `DELETE` | `/api/v1/pools/{poolId}/reservations/{batchId}` | FARMER (batch owner) | none | 200 `CancelReservationResult` {poolId: UUID, batchId: UUID, batchStatus: BatchStatus} |
| Dispatch | `POST` | `/api/v1/pools/{poolId}/dispatch` | LOGISTICS (pool owner) | none | 200 `TransportPoolDetail` (status `IN_TRANSIT`) |
| Transit telemetry: ingest | `POST` | `/api/v1/pools/{poolId}/telemetry` | LOGISTICS (pool owner) | `TelemetryIngestRequest` {tempC: number, latitude: number \| null, longitude: number \| null, recordedAt: IsoDateTime \| null} | 201 `TelemetryIngestResult` {reading: TelemetryReading, intervalHours: number, batchUpdates: BatchRulUpdate[], rerouteSuggested: boolean, suggestedRouteTier: RouteTier \| null} |
| Transit telemetry: history | `GET` | `/api/v1/pools/{poolId}/telemetry` | any | query: limit?: number, cursor?: string | 200 `Paginated<TelemetryReading>` (recordedAt ascending) |
| Arrival | `POST` | `/api/v1/pools/{poolId}/arrive` | LOGISTICS (pool owner) | none | 200 `TransportPoolDetail` (status `ARRIVED`) |
| Marketplace: browse listings | `GET` | `/api/v1/listings` | any | query: cropProfileId?: UUID, grade?: QualityGrade, minArrivalRulHours?: number, mine?: boolean, limit?: number, cursor?: string | 200 `Paginated<Listing>` |
| Marketplace: create listing | `POST` | `/api/v1/listings` | FARMER (batch owner) | `CreateListingRequest` {batchId: UUID, quantityKg: number, pricePerKgInr: number} | 201 `Listing` |
| Marketplace: get listing | `GET` | `/api/v1/listings/{listingId}` | any | none | 200 `Listing` |
| Marketplace: withdraw listing | `POST` | `/api/v1/listings/{listingId}/withdraw` | FARMER (listing owner) | none | 200 `Listing` (status `WITHDRAWN`) |
| Orders: place | `POST` | `/api/v1/orders` | BUYER | `CreateOrderRequest` {listingId: UUID, quantityKg: number} | 201 `BuyerOrder` (status `PLACED`) |
| Orders: list | `GET` | `/api/v1/orders` | BUYER (own), FARMER (on own batches), ADMIN | query: status?: OrderStatus, limit?: number, cursor?: string | 200 `Paginated<BuyerOrder>` |
| Orders: get | `GET` | `/api/v1/orders/{orderId}` | BUYER owner, FARMER of batch, ADMIN | none | 200 `BuyerOrder` |
| Dark-store intake verify | `POST` | `/api/v1/intake/verify` | BUYER (order owner) | `IntakeVerifyRequest` {orderId: UUID, scanId: UUID, storageTempC: number} | 200 `IntakeVerifyResult` {order: BuyerOrder, referenceStiffnessIndex: number, intakeStiffnessIndex: number, stiffnessDropPct: number, tolerancePct: number, result: IntakeResult} |
| Flash-markdown trigger | `POST` | `/api/v1/orders/{orderId}/markdown-check` | BUYER (order owner) | `MarkdownCheckRequest` {simulateHoursAhead: number \| null} | 200 `MarkdownCheckResult` {order: BuyerOrder, shelfRulHours: number, thresholdHours: number, markdownActive: boolean, newlyTriggered: boolean, webhookPayload: MarkdownWebhookPayload \| null} |
| Dispute: report | `POST` | `/api/v1/disputes` | BUYER (order owner), FARMER (batch owner) | `CreateDisputeRequest` {orderId: UUID, description: string} | 201 `DisputeReport` |
| Dispute: list | `GET` | `/api/v1/disputes` | BUYER, FARMER (involved), ADMIN | query: limit?: number, cursor?: string | 200 `Paginated<DisputeReport>` |
| Dispute: get | `GET` | `/api/v1/disputes/{disputeId}` | BUYER, FARMER (involved), ADMIN | none | 200 `DisputeReport` |

**Not in the API (by design):** the "Pre-book pool slot" button on the HarvestWindow card navigates to `/farmer/batches/new?advisoryId=<id>` (a pool can only be reserved for a graded batch). The FEFT-vs-FIFO comparison on the pool board is computed in the UI from `GET /pools/{poolId}` member RUL values. The live spectrogram is client-only (Web Audio AnalyserNode).

### 4.3 Behaviour rules (normative)

#### 4.3.1 Visibility and ownership

| Resource | FARMER | LOGISTICS | BUYER | ADMIN |
|---|---|---|---|---|
| Harvest advisories | own | — | — | all (read, override) |
| Batches (`GET /batches`, `GET /batches/{id}`) | own | batches in pools they carry | batches in their orders | all |
| Pools (`GET /pools`) | default `status=OPEN` | `mine=true` → own pools (any status); otherwise all | default `status=OPEN` | all |
| Listings (`GET /listings`) | `mine=true` → own (any status); otherwise `ACTIVE` | `ACTIVE` | `ACTIVE` | all |
| Orders | orders on own batches | — (`FORBIDDEN_ROLE`) | own | all |
| Disputes | on own batches | — (`FORBIDDEN_ROLE`) | own orders | all |

`mine=true` is ignored for roles not shown with it. Reading an existing resource outside the caller's scope returns `403 NOT_OWNER`.

#### 4.3.2 State machines

| Entity | Transition | Trigger |
|---|---|---|
| Batch | → `PENDING_ASSAY` | `POST /batches` |
| Batch | `PENDING_ASSAY` / `GRADED` → `GRADED` | accepted `FARM_GATE` scan |
| Batch | `GRADED` → `POOLED` | `POST /pools/{poolId}/reservations` |
| Batch | `POOLED` → `GRADED` | `DELETE /pools/{poolId}/reservations/{batchId}` |
| Batch | `POOLED` → `IN_TRANSIT` | `POST /pools/{poolId}/dispatch` |
| Batch | `IN_TRANSIT` → `ARRIVED` | `POST /pools/{poolId}/arrive` |
| Pool | → `OPEN` → `IN_TRANSIT` → `ARRIVED` | create → dispatch (needs ≥ 1 member) → arrive |
| Listing | → `ACTIVE` → `SOLD_OUT` (availableKg reaches 0) or `WITHDRAWN` | create → order / withdraw |
| Order | → `PLACED` → `INTAKE_ACCEPTED` or `INTAKE_FLAGGED` | create → `POST /intake/verify` |

Any other transition attempt returns `BATCH_STATE_INVALID` / `POOL_STATE_INVALID` / `LISTING_UNAVAILABLE` / `INTAKE_ALREADY_VERIFIED`.

#### 4.3.3 HarvestWindow algorithm (`POST /harvest-advisories`)

1. Validate `targetPickupDate` is after now and ≤ 14 days ahead, else `VALIDATION_ERROR` on field `targetPickupDate`. `hoursToPickup = (targetPickupDate − now)` in hours.
2. Fetch `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&hourly=precipitation_probability,temperature_2m,relative_humidity_2m,vapour_pressure_deficit&forecast_days=3&timezone=UTC` with `httpx`, 5 s timeout, no API key. Take the 48 hourly rows starting at the current UTC hour. Cache per (lat, lng rounded to 2 dp, UTC hour) for 30 minutes.
3. If `simulateRainInHours = h` is not null: set precipitation probability to `max(value, 90)` for hours h to h+3 (clipped to the 48-row window) and set `simulated = true`. If Open-Meteo fails and `h` is not null, continue with a neutral baseline (probability 0, temperature = crop `referenceTempC`, humidity 60, VPD 1.0) before applying h; if it fails and `h` is null, return `502 WEATHER_UNAVAILABLE`.
4. Summaries over the 48 rows: `rainProbMaxPct` = max probability; `rainExpectedInHours` = index of the first hour with probability ≥ 60, else `null`; `tempMaxC` = max temperature; `humidityMeanPct` = mean humidity; `vpdMaxKpa` = max VPD.
5. `weatherRisk` = `HIGH` if `rainProbMaxPct ≥ 60` or `tempMaxC ≥ heatStressTempC`; `MEDIUM` if `rainProbMaxPct ≥ 30`; else `LOW`.
6. `maturityFraction = min(1.5, daysSinceFlowering / harvestWindowDaysMax)`.
7. Decision — evaluate top to bottom, first match wins:

| # | Condition | recommendation | reasonCode | base confidence |
|---|---|---|---|---|
| R1 | maturityFraction ≥ 1.00 | `HARVEST_NOW` | `OVERMATURE` | 0.90 |
| R2 | maturityFraction ≥ 0.85 and weatherRisk = `HIGH` | `HARVEST_NOW` | `MATURE_WEATHER_RISK` | 0.80 |
| R3 | maturityFraction ≥ 0.85 and hoursToPickup ≤ 24 | `HARVEST_NOW` | `MATURE_PICKUP_SOON` | 0.75 |
| R4 | maturityFraction ≥ 0.60 | `RECHECK_TOMORROW` | `NEAR_MATURE_RECHECK` | 0.65 |
| R5 | otherwise | `WAIT_48H` | `IMMATURE_WAIT` | 0.85 |

   `confidence = base − 0.10` when weatherRisk = `MEDIUM`, else `base`.
8. `explanation` (English, exact templates; `{maturityPct}` = round(maturityFraction × 100)):
   - `OVERMATURE`: "Crop is at {maturityPct}% of its harvest window. Harvest now to avoid over-ripening."
   - `MATURE_WEATHER_RISK`: "Crop is at {maturityPct}% maturity and the next 48 h carry high weather risk (rain up to {rainProbMaxPct}%, max {tempMaxC} °C). Harvest before the weather turns."
   - `MATURE_PICKUP_SOON`: "Crop is at {maturityPct}% maturity and pickup is in {hoursToPickup} h. Harvest now to meet the pickup."
   - `NEAR_MATURE_RECHECK`: "Crop is at {maturityPct}% maturity. Weather risk is {weatherRisk}. Recheck tomorrow."
   - `IMMATURE_WAIT`: "Crop is at {maturityPct}% maturity. Wait about 48 h before checking again."
   The UI holds the same five templates in EN/HI/MR/TA and renders from `reasonCode` + the response fields.
9. Override: sets `overrideRecommendation`, `overrideReason`, `overriddenBy` (caller), `overriddenAt` (now). A later override replaces the earlier one. `effectiveRecommendation = overrideRecommendation ?? recommendation`. Thresholds above are placeholders until reviewed by an agronomist; the UI labels the card "Decision support — not agronomic advice".

#### 4.3.4 SonicAssay signal pipeline (backend is the source of truth)

Run on the uploaded WAV with numpy/scipy/librosa. The browser computes nothing that is persisted; its FFT is for the live spectrogram only.

1. **Decode & validate:** RIFF PCM 16-bit, mono, 44 100 or 48 000 Hz, duration 3–15 s, else `AUDIO_FORMAT_UNSUPPORTED` with `reason`. Convert to float in [-1, 1].
2. **Filter:** 4th-order Butterworth band-pass 80–3000 Hz, zero-phase (`scipy.signal.sosfiltfilt`).
3. **Noise floor:** `noiseRms` = RMS of the first 1.5 s; `noiseSpectrum` = mean magnitude spectrum of 40 ms Hann frames over that segment (same FFT size as step 5).
4. **TAP impact detection** (after 1.5 s): frame RMS with 5 ms window / 2.5 ms hop; an impact onset is the first frame with RMS > 5 × noiseRms; the impact window is the 40 ms starting at the onset; skip 250 ms after each onset before searching again. Use the first 3 impacts; fewer than 3 → `IMPACTS_NOT_DETECTED` (`impactsFound`, `required: 3`).
5. **Per-impact features:** apply Hann to the raw 40 ms window, zero-pad to 8192 points, FFT magnitude, subtract `noiseSpectrum` (floor 0). (Tap force changes amplitude, not frequency, so no amplitude normalisation is needed for f0; z-score normalisation is applied only to the MFCC input in step 8.) `f0` = frequency of the maximum magnitude in 80–3000 Hz. `spectralCentroid` = magnitude-weighted mean frequency in 80–3000 Hz. `tau`: Hilbert envelope of the (un-normalised) window, from its peak to the window end, keep samples above 2 × noiseRms, fit `ln(envelope) = a − t/τ` by least squares; τ in ms.
6. **Aggregate (TAP):** `tapF0ValuesHz` = the 3 f0 values; `f0Hz` = mean; `tapVariationPct` = population std / mean × 100; if > 12 → `SCAN_REJECTED_TAP_VARIATION` (scan not stored). `spectralCentroidHz`, `tauMs` = means over the 3 impacts.
7. **CHIRP mode:** the phone plays a 1.5 s linear sweep 100→2500 Hz starting right after the 1.5 s silence. Analyse 1.5–3.0 s: magnitude spectrum minus `noiseSpectrum`; `f0Hz` = peak in 100–2500 Hz (none above 3 × noise median → `IMPACTS_NOT_DETECTED` with `required: 1`); `tauMs = 1000 / (π × Δf)` where Δf is the −3 dB bandwidth of the peak in Hz; `tapF0ValuesHz = [f0Hz]`; `tapVariationPct = null`.
8. **MFCC:** `librosa.feature.mfcc(n_mfcc=13, n_fft=1024, hop_length=256)` over the concatenated, individually z-score-normalised impact windows (CHIRP: the analysis segment); `mfccMean` = mean per coefficient (13 values). Stored for future model training; not used for grading in v1.1.
9. **Stiffness:** `m = avgFruitMassG` form value if sent, else the batch's `avgFruitMassG`. `stiffnessIndex = f0Hz² × m^(2/3)`.
   Worked example: f0 = 410 Hz, m = 150 g → 410² = 168 100; 150^(2/3) = e^(⅔ × ln 150) = e^(3.3404) = 28.231; S = 168 100 × 28.231 ≈ **4 745 630**.
10. **Per-scan outputs:** `grade` = `A` if S ≥ `stiffnessGradeAMin`, `B` if S ≥ `stiffnessGradeBMin`, else `C`. `internalDefectFlag` = `f0Hz < defectF0MaxHz` **and** `tauMs < defectTauMaxMs`; a defect forces `grade = C`. `estimatedRulHours = rulFromCurve(S)` (step 11).
11. **`rulFromCurve(S)`:** piecewise-linear interpolation over the crop's `rulCurve` points (ascending `stiffnessIndex`); below the first point → first point's `rulHours`; above the last → last point's `rulHours`. Result is hours at `referenceTempC`. This is a calibrated lookup, labelled in the UI as "Estimated (calibration v1)".
12. Store the WAV at `{AUDIO_DIR}/{scanId}.wav` (`audio_path`, never exposed).

#### 4.3.5 Scan permissions, batch effects, idempotency

| stage | Caller | Batch status required | Effect on batch after the scan is stored |
|---|---|---|---|
| `FARM_GATE` | FARMER who owns the batch | `PENDING_ASSAY` or `GRADED` | `stiffnessIndex` = mean S of all FARM_GATE scans; `internalDefectFlag` = any FARM_GATE scan flagged; `qualityGrade` = grade(mean S), forced `C` if flagged; `initialRulHours` = `currentRulHours` = rulFromCurve(mean S); `rulUpdatedAt` = now; status `GRADED` |
| `LOADING` | LOGISTICS who owns the batch's pool | `POOLED` | `loadingStiffnessIndex` = mean S of all LOADING scans; `currentRulHours` = rulFromCurve(loadingStiffnessIndex); `rulUpdatedAt` = now |
| `INTAKE` | BUYER with an order on the batch | `ARRIVED` | none (used by `POST /intake/verify`) |

Wrong caller → `NOT_OWNER` (role allowed) or `FORBIDDEN_ROLE`; wrong status → `BATCH_STATE_INVALID`. **Idempotency:** if `clientScanId` already exists and was created by the caller, return `200` with the stored scan and the current batch (no reprocessing); if it was created by another user, `403 NOT_OWNER`. Order of checks: auth → form validation → audio content type and size → idempotency → ownership/state → WAV decode and DSP.

#### 4.3.6 Pooling, matching and FEFT

Constants: `MAX_PICKUP_RADIUS_KM = 20`, `COHORT_WINDOW_HOURS = 24`.

**FEFT tier rule** — `requiredRouteTier(rul)`: `rul < 60` → `FAST_QCOMM` (nearby dark store, < 40 km); `60 ≤ rul ≤ 120` → `FLEX_REGIONAL` (city wholesale or dark store, same day); `rul > 120` → `STANDARD_WHOLESALE` (regional wholesale, 250 km+). Tier rank for "faster": `FAST_QCOMM` 0 < `FLEX_REGIONAL` 1 < `STANDARD_WHOLESALE` 2.

**Compatibility of batch B with pool P** (all must hold; each failure adds its `CompatibilityReason`):

| Reason | Passes when |
|---|---|
| `POOL_NOT_OPEN` | `P.status = OPEN` and now < `P.pickupWindowEnd` |
| `DISTANCE_EXCEEDED` | haversine(B.pickup, P.origin) ≤ 20.0 km (Earth radius 6371 km) |
| `ETHYLENE_CONFLICT` | not (B is `SENSITIVE` and P has an `EMITTER` member) and not (B is `EMITTER` and P has a `SENSITIVE` member); `NEUTRAL` is compatible with all |
| `RUL_OUT_OF_COHORT` | `P.cohortTargetRulHours` is null, or abs(B.currentRulHours − P.cohortTargetRulHours) ≤ 24 |
| `ROUTE_TIER_MISMATCH` | `P.routeTier = requiredRouteTier(B.currentRulHours)` |
| `CAPACITY_EXCEEDED` | `P.bookedCapacityKg + B.weightKg ≤ P.maxCapacityKg` |

- **Match** (`POST /pools/match`): batch must be `GRADED` (`BATCH_STATE_INVALID` otherwise). Evaluate every pool with status `OPEN`. Compatible pools go to `matches` with `distanceKm`, `rulDeltaHours` (B − cohort target, null if empty pool), `remainingCapacityKg`, and `score = 1 − (0.5 × distanceKm / 20 + 0.5 × abs(rulDeltaHours ?? 0) / 24)`; sort by score desc, then distanceKm asc; max 10. Incompatible pools go to `rejected` (max 50) with all failing reasons.
- **Reserve:** batch `GRADED` and owned by caller; re-run compatibility → `POOL_INCOMPATIBLE` with reasons. Insert `PoolMember` with `kgBooked = B.weightKg`, `reservedAt = now`. If it is the first member, set `P.cohortTargetRulHours = B.currentRulHours`. Batch → `POOLED`.
- **Cancel:** pool `OPEN` (`POOL_STATE_INVALID` otherwise), batch in this pool and owned by caller. Delete the member row; batch → `GRADED`; if the pool is now empty, `cohortTargetRulHours = null`.
- **Computed pool fields:** `bookedCapacityKg` = sum of member `kgBooked`; `memberCount`; `ethyleneClasses` = distinct member classes in enum order; `carrierName` = carrier user's name.
- **Dispatch:** pool `OPEN` with ≥ 1 member, else `POOL_STATE_INVALID` (`reason`: "Pool has no members" or the status). For each member batch: ageing at reference temperature `currentRulHours = max(0, currentRulHours − hours(now − rulUpdatedAt))`; `rulAtDispatchHours = currentRulHours`; `rulUpdatedAt = now`; status `IN_TRANSIT`. Pool: `dispatchedAt = now`, status `IN_TRANSIT`.

#### 4.3.7 Telemetry and Q10 decay

On `POST /pools/{poolId}/telemetry` (pool must be `IN_TRANSIT`, else `POOL_STATE_INVALID`):

1. `recordedAt = body.recordedAt ?? now`. `previous = last reading's recordedAt ?? pool.dispatchedAt`. If `recordedAt ≤ previous` → `TELEMETRY_OUT_OF_ORDER`. Future times are allowed (demo simulator).
2. `intervalHours = hours(recordedAt − previous)`. The new reading's `tempC` applies to the whole interval.
3. For each member batch (crop q10, referenceTempC): `decayFactor = q10 ^ ((tempC − referenceTempC) / 10)`; `consumedHours = intervalHours × decayFactor`; `currentRulHours = max(0, previous − consumedHours)`; `rulUpdatedAt = recordedAt`. Report each in `batchUpdates`.
   Worked example (q10 = 2, ref 25 °C, start 120 h): 4 h at 25 °C → factor 1, consumed 4 h; then 6 h at 35 °C → factor 2, consumed 12 h; remaining 120 − 16 = **104 h**.
4. `suggested = requiredRouteTier(min member currentRulHours)`. `rerouteSuggested = rank(suggested) < rank(pool.routeTier)`; `suggestedRouteTier = suggested` when true, else `null`. Rerouting is advisory only (no automatic change).
5. **Arrive:** `arrivedAt = max(now, last reading recordedAt)`. Close the final interval from `max(last reading recordedAt, dispatchedAt)` to `arrivedAt` using the last reading's `tempC` (reference temperature if there are no readings), then set pool and batches to `ARRIVED`.

#### 4.3.8 Listings and orders

- **Create listing:** batch owned by caller, status `GRADED`, `POOLED` or `IN_TRANSIT` (`BATCH_STATE_INVALID` otherwise); `quantityKg ≤ batch.weightKg` (`VALIDATION_ERROR` on `quantityKg`); at most one `ACTIVE` listing per batch (`LISTING_UNAVAILABLE`). `availableKg = quantityKg`.
- **Computed listing fields** (at read time): `routeTier` = the batch's pool tier if pooled, else `requiredRouteTier(currentRulHours)`; `guaranteedArrivalRulHours = max(0, currentRulHours − TIER_TRANSIT_HOURS[routeTier])` with `TIER_TRANSIT_HOURS = { FAST_QCOMM: 6, FLEX_REGIONAL: 12, STANDARD_WHOLESALE: 24 }`; grade, defect flag, crop and pickup point come from the batch.
- **Filters:** `minArrivalRulHours` compares `guaranteedArrivalRulHours ≥ value`; `grade` and `cropProfileId` are exact matches.
- **Place order:** listing `ACTIVE` and `quantityKg ≤ availableKg`, else `LISTING_UNAVAILABLE`. Snapshot `pricePerKgInr` and `guaranteedArrivalRulHours`; `totalPriceInr = quantityKg × pricePerKgInr`; `markdownPct = 0`. Decrease `availableKg`; when it reaches 0 the listing becomes `SOLD_OUT`. No payment is taken (simulated ledger only).
- **Withdraw:** listing `ACTIVE` and owned by caller, else `LISTING_UNAVAILABLE`. Existing orders are unaffected.

#### 4.3.9 Dark-store intake and markdown

- **Intake verify:** caller owns the order; order status `PLACED` (else `INTAKE_ALREADY_VERIFIED`); `scanId` must be an `INTAKE` scan of `order.batchId` created by the caller (else `SCAN_MISMATCH`).
  `reference = batch.loadingStiffnessIndex ?? batch.stiffnessIndex`; `stiffnessDropPct = (reference − scan.stiffnessIndex) / reference × 100` (negative means firmer); `tolerancePct = crop.intakeStiffnessTolerancePct`; `result = ACCEPTED` if `stiffnessDropPct ≤ tolerancePct`, else `FLAGGED`.
  Update the order: `intakeScanId`, `intakeResult`, `intakeStiffnessDropPct`, `rulAtIntakeHours = scan.estimatedRulHours`, `storageTempC`, `intakeVerifiedAt = now`, status `INTAKE_ACCEPTED` / `INTAKE_FLAGGED`.
- **Shelf RUL** at time t: `shelfRul(t) = max(0, rulAtIntakeHours − hours(t − intakeVerifiedAt) × q10 ^ ((storageTempC − referenceTempC) / 10))`.
- **Markdown check:** caller owns the order and intake is verified (else `INTAKE_NOT_VERIFIED`). `t = now + (simulateHoursAhead ?? 0) h`; `shelfRulHours = shelfRul(t)`; `thresholdHours = crop.markdownThresholdHours` (24 by default). If `shelfRulHours < thresholdHours` and `markdownTriggeredAt` is null: set `markdownPct = crop.defaultMarkdownPct`, `markdownTriggeredAt = now`, `newlyTriggered = true`, build `webhookPayload` and log it (simulated webhook: no outbound HTTP call). Otherwise `newlyTriggered = false`, `webhookPayload = null`. `markdownActive = markdownTriggeredAt != null`. Simulated hours are never persisted except through a triggered markdown.

#### 4.3.10 Dispute ledger

Caller is the order's buyer or the batch's farmer; intake must be verified (`INTAKE_NOT_VERIFIED`); one dispute per order (`DISPUTE_ALREADY_EXISTS`). Checkpoints:

| Checkpoint | Time | RUL (hours) |
|---|---|---|
| Farm gate | `farmGateAt` = latest FARM_GATE scan `recordedAt` | `rulFarmGateHours = batch.initialRulHours` |
| Loading | if LOADING scans exist: latest LOADING `recordedAt`, source `SCAN`; else `pool.dispatchedAt`, source `MODEL` | `SCAN`: rulFromCurve(loadingStiffnessIndex); `MODEL`: `batch.rulAtDispatchHours` |
| Intake | `intakeAt = order.intakeVerifiedAt` | `rulIntakeHours = order.rulAtIntakeHours` |
| Shelf | `assessedAt` = now | `rulShelfHours = shelfRul(now)` |

Segments in fixed order `FARM` (farm gate → loading), `TRANSIT` (loading → intake), `BUYER_STORAGE` (intake → assessed): `elapsedHours = max(0, hours(end − start))`; `actualLossHours = startRul − endRul`; `expectedLossHours = elapsedHours` (normal ageing at reference temperature); `excessLossHours = actualLossHours − expectedLossHours`. `responsibleParty` = party of the segment with the largest `excessLossHours` if it exceeds `crop.disputeToleranceHours` (6 by default), else `NONE`. The UI states that `BUYER_STORAGE` loss is modelled from the declared storage temperature, while `FARM` and `TRANSIT` are measured when scans exist.

### 4.4 Worked request / response examples

`POST /api/v1/harvest-advisories`

```json
{ "cropProfileId": "8b1e4f0a-3c2d-4e5f-9a1b-2c3d4e5f6a7b", "daysSinceFlowering": 48, "targetPickupDate": "2026-10-26T04:30:00Z", "latitude": 20.011, "longitude": 73.79, "simulateRainInHours": 30 }
```

```json
{
  "success": true,
  "data": {
    "id": "0d6c2a8e-5f4b-4a3c-9e2d-1b0a9f8e7d6c", "farmerId": "5a4b3c2d-1e0f-4a9b-8c7d-6e5f4a3b2c1d",
    "cropProfileId": "8b1e4f0a-3c2d-4e5f-9a1b-2c3d4e5f6a7b", "cropName": "TOMATO",
    "daysSinceFlowering": 48, "targetPickupDate": "2026-10-26T04:30:00Z", "latitude": 20.011, "longitude": 73.79,
    "maturityFraction": 0.87, "hoursToPickup": 40.5,
    "rainProbMaxPct": 90.0, "rainExpectedInHours": 30.0, "tempMaxC": 31.2, "humidityMeanPct": 71.4, "vpdMaxKpa": 1.6,
    "weatherRisk": "HIGH", "simulated": true,
    "recommendation": "HARVEST_NOW", "reasonCode": "MATURE_WEATHER_RISK", "confidence": 0.8,
    "explanation": "Crop is at 87% maturity and the next 48 h carry high weather risk (rain up to 90.0%, max 31.2 °C). Harvest before the weather turns.",
    "overrideRecommendation": null, "overrideReason": null, "overriddenBy": null, "overriddenAt": null,
    "effectiveRecommendation": "HARVEST_NOW", "createdAt": "2026-10-24T12:00:00Z"
  }
}
```

`POST /api/v1/assay/sonic-scans` (curl, for backend testing)

```bash
curl -X POST http://localhost:8000/api/v1/assay/sonic-scans \
  -H "Authorization: Bearer $TOKEN" \
  -F "audio=@scan.wav;type=audio/wav" -F "batchId=$BATCH_ID" -F "stage=FARM_GATE" -F "mode=TAP" \
  -F "clientScanId=$(uuidgen | tr A-Z a-z)" -F "recordedAt=2026-10-24T12:00:00Z"
```

Rejected scan (`422`):

```json
{ "success": false, "error": { "code": "SCAN_REJECTED_TAP_VARIATION", "message": "Taps were inconsistent. Tap the same spot on the fruit's equator again.", "details": { "tapF0ValuesHz": [412.3, 330.0, 480.5], "tapVariationPct": 15.1, "maxAllowedPct": 12 } } }
```


---

## 5. CANONICAL DATA SCHEMAS

### 5.1 Entity map

Each entity exists as (A) a TypeScript interface in 5.2 and (B) a Pydantic model in 5.3 with the same name, plus (for stored entities) a SQL table in 5.4. JSON field names are identical after `to_camel(snake_name)`. "Computed" fields are filled by the service layer from joins or formulas; "internal" columns are never serialised.

| Entity | TS interface / Pydantic model | SQL table | Computed (not stored) | Internal columns |
|---|---|---|---|---|
| User | `User` | `users` | — | `password_hash` |
| CropProfile | `CropProfile` | `crop_profiles` | — | — |
| HarvestAdvisory | `HarvestAdvisory` | `harvest_advisories` | `cropName`, `effectiveRecommendation` | — |
| HarvestBatch | `HarvestBatch` | `harvest_batches` | `farmerName`, `cropName`, `ethyleneClass`, `poolId`, `qrCodeValue` | — |
| AcousticScan | `AcousticScan` | `acoustic_scans` | — | `audio_path` |
| TransportPool | `TransportPool` / `TransportPoolDetail` | `transport_pools` | `carrierName`, `bookedCapacityKg`, `memberCount`, `ethyleneClasses`, `members` | — |
| PoolMember | `PoolMember` | `pool_members` | `farmerId`, `farmerName`, `cropName`, `ethyleneClass`, `currentRulHours` | — |
| TelemetryReading | `TelemetryReading` | `telemetry_readings` | — | — |
| Listing | `Listing` | `listings` | `farmerName`, `cropProfileId`, `cropName`, `qualityGrade`, `internalDefectFlag`, `currentRulHours`, `routeTier`, `guaranteedArrivalRulHours`, `pickupLatitude`, `pickupLongitude` | — |
| BuyerOrder | `BuyerOrder` | `buyer_orders` | `buyerName`, `cropName` | — |
| DisputeReport | `DisputeReport` (+ `DisputeSegment` in JSON column) | `dispute_reports` | — | — |
| Request DTOs | `RegisterRequest`, `LoginRequest`, `UpdateProfileRequest`, `CropProfileUpsertRequest`, `HarvestAdvisoryRequest`, `AdvisoryOverrideRequest`, `CreateBatchRequest`, `SonicScanFormFields` ↔ `SonicScanForm`, `CreatePoolRequest`, `PoolMatchRequest`, `CreateReservationRequest`, `TelemetryIngestRequest`, `CreateListingRequest`, `CreateOrderRequest`, `IntakeVerifyRequest`, `MarkdownCheckRequest`, `CreateDisputeRequest` | — | — | — |
| Response DTOs | `AuthResponse`, `SonicScanResult`, `BatchPassport`, `PoolMatch`, `PoolRejection`, `PoolMatchResult`, `CancelReservationResult`, `BatchRulUpdate`, `TelemetryIngestResult`, `IntakeVerifyResult`, `MarkdownWebhookPayload`, `MarkdownCheckResult`, `HealthStatus` | — | — | — |
| Envelopes & errors | `ApiSuccess<T>`, `Paginated<T>`, `ApiErrorResponse`, `ApiErrorBody`, `ValidationFieldError` | — | — | — |
| Value objects | `LocalizedText`, `RulCurvePoint` | JSON columns | — | — |

`qrCodeValue` = `{FRONTEND_BASE_URL}/passport/{batch.id}` (env `FRONTEND_BASE_URL`, default `http://localhost:3000`). `SonicScanFormFields.audio` is the file part; it has no Pydantic field (handled as `UploadFile`).

### 5.2 TypeScript (`lib/api/types.ts`, copy verbatim)

```ts
// FarmPool 360 x ChronoCrop — API contract types (v1.1.0)
// Frontend copy: lib/api/types.ts. Generated from PRD Section 5. Do not edit by hand.
// Every key is camelCase. "T | null" = key always present, value may be null.
// "key?: T" (omittable) appears ONLY in: UpdateProfileRequest (PATCH), SonicScanFormFields
// (optional multipart fields) and ApiRoutes query objects (optional query params).

// ───────────────────────── Primitives ─────────────────────────
/** RFC 4122 UUID v4, lowercase, hyphenated. Example: "3f2b8c1e-9a4d-4c2b-8f1e-2d7a6b5c4e3f" */
export type UUID = string;
/** ISO 8601 UTC, seconds precision, trailing Z. Example: "2026-10-24T12:00:00Z" */
export type IsoDateTime = string;

// ───────────────────────── Enums ─────────────────────────
export const ROLES = ["FARMER", "LOGISTICS", "BUYER", "ADMIN"] as const;
export type Role = (typeof ROLES)[number];
export type RegisterRole = Exclude<Role, "ADMIN">;

export const LANGUAGES = ["EN", "HI", "MR", "TA"] as const;
export type Language = (typeof LANGUAGES)[number];

export const THEMES = ["LIGHT", "DARK", "SYSTEM"] as const;
export type Theme = (typeof THEMES)[number];

export const ETHYLENE_CLASSES = ["EMITTER", "SENSITIVE", "NEUTRAL"] as const;
export type EthyleneClass = (typeof ETHYLENE_CLASSES)[number];

export const RECOMMENDATIONS = ["HARVEST_NOW", "RECHECK_TOMORROW", "WAIT_48H"] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export const ADVISORY_REASON_CODES = [
  "OVERMATURE",
  "MATURE_WEATHER_RISK",
  "MATURE_PICKUP_SOON",
  "NEAR_MATURE_RECHECK",
  "IMMATURE_WAIT",
] as const;
export type AdvisoryReasonCode = (typeof ADVISORY_REASON_CODES)[number];

export const WEATHER_RISKS = ["LOW", "MEDIUM", "HIGH"] as const;
export type WeatherRisk = (typeof WEATHER_RISKS)[number];

export const BATCH_STATUSES = ["PENDING_ASSAY", "GRADED", "POOLED", "IN_TRANSIT", "ARRIVED"] as const;
export type BatchStatus = (typeof BATCH_STATUSES)[number];

export const QUALITY_GRADES = ["A", "B", "C"] as const;
export type QualityGrade = (typeof QUALITY_GRADES)[number];

export const SCAN_STAGES = ["FARM_GATE", "LOADING", "INTAKE"] as const;
export type ScanStage = (typeof SCAN_STAGES)[number];

export const SCAN_MODES = ["TAP", "CHIRP"] as const;
export type ScanMode = (typeof SCAN_MODES)[number];

export const ROUTE_TIERS = ["FAST_QCOMM", "FLEX_REGIONAL", "STANDARD_WHOLESALE"] as const;
export type RouteTier = (typeof ROUTE_TIERS)[number];

export const POOL_STATUSES = ["OPEN", "IN_TRANSIT", "ARRIVED"] as const;
export type PoolStatus = (typeof POOL_STATUSES)[number];

export const COMPATIBILITY_REASONS = [
  "POOL_NOT_OPEN",
  "DISTANCE_EXCEEDED",
  "ETHYLENE_CONFLICT",
  "RUL_OUT_OF_COHORT",
  "ROUTE_TIER_MISMATCH",
  "CAPACITY_EXCEEDED",
] as const;
export type CompatibilityReason = (typeof COMPATIBILITY_REASONS)[number];

export const LISTING_STATUSES = ["ACTIVE", "SOLD_OUT", "WITHDRAWN"] as const;
export type ListingStatus = (typeof LISTING_STATUSES)[number];

export const ORDER_STATUSES = ["PLACED", "INTAKE_ACCEPTED", "INTAKE_FLAGGED"] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const INTAKE_RESULTS = ["ACCEPTED", "FLAGGED"] as const;
export type IntakeResult = (typeof INTAKE_RESULTS)[number];

export const RESPONSIBLE_PARTIES = ["FARM", "TRANSIT", "BUYER_STORAGE", "NONE"] as const;
export type ResponsibleParty = (typeof RESPONSIBLE_PARTIES)[number];

export const CHECKPOINT_SOURCES = ["SCAN", "MODEL"] as const;
export type CheckpointSource = (typeof CHECKPOINT_SOURCES)[number];

export const ERROR_CODES = [
  "VALIDATION_ERROR",
  "AUTH_REQUIRED",
  "TOKEN_INVALID",
  "TOKEN_EXPIRED",
  "INVALID_CREDENTIALS",
  "FORBIDDEN_ROLE",
  "NOT_OWNER",
  "NOT_FOUND",
  "METHOD_NOT_ALLOWED",
  "PHONE_ALREADY_REGISTERED",
  "BATCH_STATE_INVALID",
  "POOL_STATE_INVALID",
  "POOL_INCOMPATIBLE",
  "LISTING_UNAVAILABLE",
  "SCAN_MISMATCH",
  "INTAKE_NOT_VERIFIED",
  "INTAKE_ALREADY_VERIFIED",
  "DISPUTE_ALREADY_EXISTS",
  "TELEMETRY_OUT_OF_ORDER",
  "AUDIO_TOO_LARGE",
  "AUDIO_FORMAT_UNSUPPORTED",
  "IMPACTS_NOT_DETECTED",
  "SCAN_REJECTED_TAP_VARIATION",
  "WEATHER_UNAVAILABLE",
  "INTERNAL_ERROR",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];
/** Frontend-only codes, never sent by the backend. */
export type ClientErrorCode = ErrorCode | "NETWORK_ERROR" | "INVALID_RESPONSE";

// ───────────────────────── Envelopes ─────────────────────────
export interface ApiSuccess<T> {
  success: true;
  data: T;
}
export interface Paginated<T> {
  items: T[];
  nextCursor: string | null;
}
export interface ValidationFieldError {
  /** Dotted camelCase path, e.g. "pickupLatitude" or "rulCurve.0.rulHours" */
  field: string;
  message: string;
  type: string;
}
export interface ApiErrorBody {
  code: ErrorCode;
  message: string;
  /** VALIDATION_ERROR → { fields: ValidationFieldError[] }; other codes → see Section 3 table */
  details: Record<string, unknown>;
}
export interface ApiErrorResponse {
  success: false;
  error: ApiErrorBody;
}
export type ApiResponse<T> = ApiSuccess<T> | ApiErrorResponse;

// ───────────────────────── Shared value objects ─────────────────────────
export interface LocalizedText {
  en: string;
  hi: string;
  mr: string;
  ta: string;
}
export interface RulCurvePoint {
  /** Cooke stiffness index, Hz^2·g^(2/3) */
  stiffnessIndex: number;
  /** Remaining useful life at referenceTempC, hours */
  rulHours: number;
}
export interface HealthStatus {
  status: "OK";
  version: string;
}

// ───────────────────────── Auth & User ─────────────────────────
export interface User {
  id: UUID;
  name: string;
  phone: string;
  role: Role;
  language: Language;
  theme: Theme;
  organizationName: string | null;
  homeLatitude: number | null;
  homeLongitude: number | null;
  createdAt: IsoDateTime;
}
export interface RegisterRequest {
  /** 2–80 chars */
  name: string;
  /** E.164, regex ^\+[1-9][0-9]{9,14}$ e.g. "+919800000001" */
  phone: string;
  /** 8–72 chars */
  password: string;
  role: RegisterRole;
  language: Language;
  /** 2–120 chars or null */
  organizationName: string | null;
}
export interface LoginRequest {
  phone: string;
  password: string;
}
export interface AuthResponse {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: IsoDateTime;
  user: User;
}
/** PATCH: omit a key to leave it unchanged. null allowed only where typed "| null". */
export interface UpdateProfileRequest {
  name?: string;
  language?: Language;
  theme?: Theme;
  organizationName?: string | null;
  /** homeLatitude and homeLongitude must be sent together (both numbers or both null) */
  homeLatitude?: number | null;
  homeLongitude?: number | null;
}

// ───────────────────────── Crop profiles ─────────────────────────
export interface CropProfile {
  id: UUID;
  /** UPPER_SNAKE key, regex ^[A-Z][A-Z0-9_]{1,49}$, e.g. "TOMATO" */
  cropName: string;
  displayName: LocalizedText;
  ethyleneClass: EthyleneClass;
  harvestWindowDaysMin: number;
  harvestWindowDaysMax: number;
  heatStressTempC: number;
  typicalFruitMassGMin: number;
  typicalFruitMassGMax: number;
  stiffnessGradeAMin: number;
  stiffnessGradeBMin: number;
  defectF0MaxHz: number;
  defectTauMaxMs: number;
  /** ≥ 2 points, strictly ascending by stiffnessIndex */
  rulCurve: RulCurvePoint[];
  q10: number;
  referenceTempC: number;
  intakeStiffnessTolerancePct: number;
  markdownThresholdHours: number;
  defaultMarkdownPct: number;
  disputeToleranceHours: number;
  calibrationNote: string;
  updatedAt: IsoDateTime;
}
export interface CropProfileUpsertRequest {
  cropName: string;
  displayName: LocalizedText;
  ethyleneClass: EthyleneClass;
  harvestWindowDaysMin: number;
  harvestWindowDaysMax: number;
  heatStressTempC: number;
  typicalFruitMassGMin: number;
  typicalFruitMassGMax: number;
  stiffnessGradeAMin: number;
  stiffnessGradeBMin: number;
  defectF0MaxHz: number;
  defectTauMaxMs: number;
  rulCurve: RulCurvePoint[];
  q10: number;
  referenceTempC: number;
  intakeStiffnessTolerancePct: number;
  markdownThresholdHours: number;
  defaultMarkdownPct: number;
  disputeToleranceHours: number;
  calibrationNote: string;
}

// ───────────────────────── HarvestWindow ─────────────────────────
export interface HarvestAdvisoryRequest {
  cropProfileId: UUID;
  /** integer 0–365 */
  daysSinceFlowering: number;
  /** must be in the future and ≤ 14 days ahead */
  targetPickupDate: IsoDateTime;
  latitude: number;
  longitude: number;
  /** demo toggle: integer 0–47 = force ≥ 90% rain probability from that hour for 4 h; null = real forecast only */
  simulateRainInHours: number | null;
}
export interface HarvestAdvisory {
  id: UUID;
  farmerId: UUID;
  cropProfileId: UUID;
  cropName: string;
  daysSinceFlowering: number;
  targetPickupDate: IsoDateTime;
  latitude: number;
  longitude: number;
  /** daysSinceFlowering / harvestWindowDaysMax, 0–1.5, 2 dp */
  maturityFraction: number;
  hoursToPickup: number;
  /** Weather fields below summarise the next 48 h of the Open-Meteo hourly forecast */
  rainProbMaxPct: number;
  rainExpectedInHours: number | null;
  tempMaxC: number;
  humidityMeanPct: number;
  vpdMaxKpa: number;
  weatherRisk: WeatherRisk;
  simulated: boolean;
  recommendation: Recommendation;
  reasonCode: AdvisoryReasonCode;
  /** 0–1, 2 dp */
  confidence: number;
  /** English only; UI renders localized text from reasonCode */
  explanation: string;
  overrideRecommendation: Recommendation | null;
  overrideReason: string | null;
  overriddenBy: UUID | null;
  overriddenAt: IsoDateTime | null;
  /** overrideRecommendation ?? recommendation */
  effectiveRecommendation: Recommendation;
  createdAt: IsoDateTime;
}
export interface AdvisoryOverrideRequest {
  overrideRecommendation: Recommendation;
  /** 5–500 chars */
  overrideReason: string;
}

// ───────────────────────── Batches & Passport ─────────────────────────
export interface CreateBatchRequest {
  cropProfileId: UUID;
  /** > 0, ≤ 50000 */
  weightKg: number;
  /** > 0, ≤ 20000 */
  avgFruitMassG: number;
  harvestedAt: IsoDateTime;
  pickupLatitude: number;
  pickupLongitude: number;
  harvestAdvisoryId: UUID | null;
}
export interface HarvestBatch {
  id: UUID;
  farmerId: UUID;
  farmerName: string;
  cropProfileId: UUID;
  cropName: string;
  ethyleneClass: EthyleneClass;
  harvestAdvisoryId: UUID | null;
  weightKg: number;
  avgFruitMassG: number;
  harvestedAt: IsoDateTime;
  pickupLatitude: number;
  pickupLongitude: number;
  status: BatchStatus;
  qualityGrade: QualityGrade | null;
  internalDefectFlag: boolean;
  stiffnessIndex: number | null;
  loadingStiffnessIndex: number | null;
  initialRulHours: number | null;
  currentRulHours: number | null;
  rulUpdatedAt: IsoDateTime | null;
  rulAtDispatchHours: number | null;
  poolId: UUID | null;
  /** `${FRONTEND_BASE_URL}/passport/${id}` — encode this string in the QR */
  qrCodeValue: string;
  createdAt: IsoDateTime;
}
export interface AcousticScan {
  id: UUID;
  batchId: UUID;
  stage: ScanStage;
  mode: ScanMode;
  clientScanId: UUID;
  f0Hz: number;
  /** TAP: 3 values (one per tap). CHIRP: 1 value. */
  tapF0ValuesHz: number[];
  /** TAP: coefficient of variation of tapF0ValuesHz in %. CHIRP: null */
  tapVariationPct: number | null;
  spectralCentroidHz: number;
  tauMs: number;
  /** exactly 13 values */
  mfccMean: number[];
  avgFruitMassG: number;
  stiffnessIndex: number;
  estimatedRulHours: number;
  grade: QualityGrade;
  internalDefectFlag: boolean;
  phoneModel: string | null;
  sampleRateHz: number;
  scannedBy: UUID;
  recordedAt: IsoDateTime;
  createdAt: IsoDateTime;
}
/** multipart/form-data fields for POST /assay/sonic-scans (all values are strings on the wire) */
export interface SonicScanFormFields {
  /** WAV file: RIFF PCM 16-bit, mono, 44100 or 48000 Hz, 3–15 s, ≤ 2 MB, filename "scan.wav", type "audio/wav" */
  audio: Blob;
  batchId: UUID;
  stage: ScanStage;
  mode: ScanMode;
  clientScanId: UUID;
  recordedAt: IsoDateTime;
  /** optional: omit the field entirely when unknown (never send "null") */
  phoneModel?: string;
  /** optional: omit to use the batch's avgFruitMassG */
  avgFruitMassG?: string;
}
export interface SonicScanResult {
  scan: AcousticScan;
  batch: HarvestBatch;
}

// ───────────────────────── Pools & Telemetry ─────────────────────────
export interface CreatePoolRequest {
  routeTier: RouteTier;
  originLabel: string;
  originLatitude: number;
  originLongitude: number;
  destinationName: string;
  destinationLatitude: number;
  destinationLongitude: number;
  /** > 0, ≤ 40000 */
  maxCapacityKg: number;
  pickupWindowStart: IsoDateTime;
  pickupWindowEnd: IsoDateTime;
}
export interface TransportPool {
  id: UUID;
  carrierId: UUID;
  carrierName: string;
  routeTier: RouteTier;
  status: PoolStatus;
  originLabel: string;
  originLatitude: number;
  originLongitude: number;
  destinationName: string;
  destinationLatitude: number;
  destinationLongitude: number;
  maxCapacityKg: number;
  bookedCapacityKg: number;
  memberCount: number;
  cohortTargetRulHours: number | null;
  ethyleneClasses: EthyleneClass[];
  pickupWindowStart: IsoDateTime;
  pickupWindowEnd: IsoDateTime;
  dispatchedAt: IsoDateTime | null;
  arrivedAt: IsoDateTime | null;
  createdAt: IsoDateTime;
}
export interface PoolMember {
  id: UUID;
  poolId: UUID;
  batchId: UUID;
  farmerId: UUID;
  farmerName: string;
  cropName: string;
  ethyleneClass: EthyleneClass;
  kgBooked: number;
  currentRulHours: number | null;
  reservedAt: IsoDateTime;
}
export interface TransportPoolDetail extends TransportPool {
  members: PoolMember[];
}
export interface PoolMatchRequest {
  batchId: UUID;
}
export interface PoolMatch {
  pool: TransportPool;
  distanceKm: number;
  /** null when the pool has no members yet */
  rulDeltaHours: number | null;
  remainingCapacityKg: number;
  /** 0–1, higher is better, 3 dp */
  score: number;
}
export interface PoolRejection {
  poolId: UUID;
  reasons: CompatibilityReason[];
}
export interface PoolMatchResult {
  batchId: UUID;
  batchRulHours: number;
  requiredRouteTier: RouteTier;
  matches: PoolMatch[];
  rejected: PoolRejection[];
}
export interface CreateReservationRequest {
  batchId: UUID;
}
export interface CancelReservationResult {
  poolId: UUID;
  batchId: UUID;
  batchStatus: BatchStatus;
}
export interface TelemetryIngestRequest {
  /** -10 to 60 */
  tempC: number;
  latitude: number | null;
  longitude: number | null;
  /** null = server time now. Demo simulator may send future times; must be later than the previous reading. */
  recordedAt: IsoDateTime | null;
}
export interface TelemetryReading {
  id: UUID;
  poolId: UUID;
  tempC: number;
  latitude: number | null;
  longitude: number | null;
  recordedAt: IsoDateTime;
  createdAt: IsoDateTime;
}
export interface BatchRulUpdate {
  batchId: UUID;
  previousRulHours: number;
  decayFactor: number;
  consumedHours: number;
  currentRulHours: number;
}
export interface TelemetryIngestResult {
  reading: TelemetryReading;
  intervalHours: number;
  batchUpdates: BatchRulUpdate[];
  rerouteSuggested: boolean;
  suggestedRouteTier: RouteTier | null;
}

// ───────────────────────── Marketplace & Orders ─────────────────────────
export interface CreateListingRequest {
  batchId: UUID;
  /** > 0 and ≤ batch.weightKg */
  quantityKg: number;
  /** > 0, ≤ 100000 */
  pricePerKgInr: number;
}
export interface Listing {
  id: UUID;
  batchId: UUID;
  farmerId: UUID;
  farmerName: string;
  cropProfileId: UUID;
  cropName: string;
  qualityGrade: QualityGrade;
  internalDefectFlag: boolean;
  quantityKg: number;
  availableKg: number;
  pricePerKgInr: number;
  currentRulHours: number;
  routeTier: RouteTier;
  guaranteedArrivalRulHours: number;
  pickupLatitude: number;
  pickupLongitude: number;
  status: ListingStatus;
  createdAt: IsoDateTime;
}
export interface CreateOrderRequest {
  listingId: UUID;
  /** > 0 and ≤ listing.availableKg */
  quantityKg: number;
}
export interface BuyerOrder {
  id: UUID;
  buyerId: UUID;
  buyerName: string;
  listingId: UUID;
  batchId: UUID;
  cropName: string;
  quantityKg: number;
  pricePerKgInr: number;
  totalPriceInr: number;
  guaranteedArrivalRulHours: number;
  status: OrderStatus;
  intakeScanId: UUID | null;
  intakeResult: IntakeResult | null;
  intakeStiffnessDropPct: number | null;
  rulAtIntakeHours: number | null;
  storageTempC: number | null;
  intakeVerifiedAt: IsoDateTime | null;
  markdownPct: number;
  markdownTriggeredAt: IsoDateTime | null;
  createdAt: IsoDateTime;
}

// ───────────────────────── Dark-store intake & markdown ─────────────────────────
export interface IntakeVerifyRequest {
  orderId: UUID;
  scanId: UUID;
  /** -5 to 45 */
  storageTempC: number;
}
export interface IntakeVerifyResult {
  order: BuyerOrder;
  referenceStiffnessIndex: number;
  intakeStiffnessIndex: number;
  stiffnessDropPct: number;
  tolerancePct: number;
  result: IntakeResult;
}
export interface MarkdownCheckRequest {
  /** demo fast-forward: 0–240 hours, or null for "now" */
  simulateHoursAhead: number | null;
}
export interface MarkdownWebhookPayload {
  event: "FLASH_MARKDOWN";
  orderId: UUID;
  batchId: UUID;
  cropName: string;
  markdownPct: number;
  shelfRulHours: number;
  triggeredAt: IsoDateTime;
}
export interface MarkdownCheckResult {
  order: BuyerOrder;
  shelfRulHours: number;
  thresholdHours: number;
  markdownActive: boolean;
  newlyTriggered: boolean;
  /** non-null only when newlyTriggered is true */
  webhookPayload: MarkdownWebhookPayload | null;
}

// ───────────────────────── Disputes ─────────────────────────
export interface CreateDisputeRequest {
  orderId: UUID;
  /** 10–1000 chars */
  description: string;
}
export interface DisputeSegment {
  /** never "NONE" */
  party: ResponsibleParty;
  startAt: IsoDateTime;
  endAt: IsoDateTime;
  elapsedHours: number;
  actualLossHours: number;
  expectedLossHours: number;
  excessLossHours: number;
}
export interface DisputeReport {
  id: UUID;
  orderId: UUID;
  batchId: UUID;
  raisedBy: UUID;
  raisedByRole: Role;
  description: string;
  rulFarmGateHours: number;
  rulLoadingHours: number;
  rulIntakeHours: number;
  rulShelfHours: number;
  farmGateAt: IsoDateTime;
  loadingAt: IsoDateTime;
  intakeAt: IsoDateTime;
  assessedAt: IsoDateTime;
  loadingCheckpointSource: CheckpointSource;
  /** always 3 items in order FARM, TRANSIT, BUYER_STORAGE */
  segments: DisputeSegment[];
  responsibleParty: ResponsibleParty;
  createdAt: IsoDateTime;
}

// ───────────────────────── Batch passport (public) ─────────────────────────
export interface BatchPassport {
  batch: HarvestBatch;
  /** all scans for the batch, ascending by recordedAt */
  scans: AcousticScan[];
  pool: TransportPool | null;
  /** pool telemetry, ascending by recordedAt; [] if not pooled */
  telemetry: TelemetryReading[];
}

// ───────────────────────── Route map (single source for the API client) ─────────────────────────
// Key = "METHOD /path" relative to /api/v1. ":param" = path param. query = query-string params.
// body "multipart" = FormData built from SonicScanFormFields. body null = send no body.
export interface ApiRoutes {
  "GET /health": { query: null; body: null; res: HealthStatus };
  "POST /auth/register": { query: null; body: RegisterRequest; res: AuthResponse };
  "POST /auth/login": { query: null; body: LoginRequest; res: AuthResponse };
  "GET /users/me": { query: null; body: null; res: User };
  "PATCH /users/me": { query: null; body: UpdateProfileRequest; res: User };
  "GET /crop-profiles": { query: { limit?: number; cursor?: string }; body: null; res: Paginated<CropProfile> };
  "GET /crop-profiles/:cropProfileId": { query: null; body: null; res: CropProfile };
  "POST /crop-profiles": { query: null; body: CropProfileUpsertRequest; res: CropProfile };
  "PUT /crop-profiles/:cropProfileId": { query: null; body: CropProfileUpsertRequest; res: CropProfile };
  "POST /harvest-advisories": { query: null; body: HarvestAdvisoryRequest; res: HarvestAdvisory };
  "GET /harvest-advisories": { query: { limit?: number; cursor?: string }; body: null; res: Paginated<HarvestAdvisory> };
  "GET /harvest-advisories/:advisoryId": { query: null; body: null; res: HarvestAdvisory };
  "POST /harvest-advisories/:advisoryId/override": { query: null; body: AdvisoryOverrideRequest; res: HarvestAdvisory };
  "POST /batches": { query: null; body: CreateBatchRequest; res: HarvestBatch };
  "GET /batches": { query: { status?: BatchStatus; limit?: number; cursor?: string }; body: null; res: Paginated<HarvestBatch> };
  "GET /batches/:batchId": { query: null; body: null; res: HarvestBatch };
  "GET /passport/:batchId": { query: null; body: null; res: BatchPassport };
  "POST /assay/sonic-scans": { query: null; body: "multipart"; res: SonicScanResult };
  "GET /pools": { query: { status?: PoolStatus; routeTier?: RouteTier; mine?: boolean; limit?: number; cursor?: string }; body: null; res: Paginated<TransportPool> };
  "POST /pools": { query: null; body: CreatePoolRequest; res: TransportPoolDetail };
  "GET /pools/:poolId": { query: null; body: null; res: TransportPoolDetail };
  "POST /pools/match": { query: null; body: PoolMatchRequest; res: PoolMatchResult };
  "POST /pools/:poolId/reservations": { query: null; body: CreateReservationRequest; res: PoolMember };
  "DELETE /pools/:poolId/reservations/:batchId": { query: null; body: null; res: CancelReservationResult };
  "POST /pools/:poolId/dispatch": { query: null; body: null; res: TransportPoolDetail };
  "POST /pools/:poolId/telemetry": { query: null; body: TelemetryIngestRequest; res: TelemetryIngestResult };
  "GET /pools/:poolId/telemetry": { query: { limit?: number; cursor?: string }; body: null; res: Paginated<TelemetryReading> };
  "POST /pools/:poolId/arrive": { query: null; body: null; res: TransportPoolDetail };
  "GET /listings": { query: { cropProfileId?: UUID; grade?: QualityGrade; minArrivalRulHours?: number; mine?: boolean; limit?: number; cursor?: string }; body: null; res: Paginated<Listing> };
  "POST /listings": { query: null; body: CreateListingRequest; res: Listing };
  "GET /listings/:listingId": { query: null; body: null; res: Listing };
  "POST /listings/:listingId/withdraw": { query: null; body: null; res: Listing };
  "POST /orders": { query: null; body: CreateOrderRequest; res: BuyerOrder };
  "GET /orders": { query: { status?: OrderStatus; limit?: number; cursor?: string }; body: null; res: Paginated<BuyerOrder> };
  "GET /orders/:orderId": { query: null; body: null; res: BuyerOrder };
  "POST /intake/verify": { query: null; body: IntakeVerifyRequest; res: IntakeVerifyResult };
  "POST /orders/:orderId/markdown-check": { query: null; body: MarkdownCheckRequest; res: MarkdownCheckResult };
  "POST /disputes": { query: null; body: CreateDisputeRequest; res: DisputeReport };
  "GET /disputes": { query: { limit?: number; cursor?: string }; body: null; res: Paginated<DisputeReport> };
  "GET /disputes/:disputeId": { query: null; body: null; res: DisputeReport };
}
export type ApiRouteKey = keyof ApiRoutes;
```

### 5.3 Pydantic v2 (`app/schemas.py`, copy verbatim)

```python
# FarmPool 360 x ChronoCrop — API contract schemas (v1.1.0)
# Backend copy: app/schemas.py. Generated from PRD Section 5. Do not edit by hand.
# Requires: Python >= 3.11, pydantic >= 2.11, < 3.
# snake_case attributes <-> camelCase JSON in both directions via CamelModel.
from datetime import datetime, timezone
from enum import StrEnum
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
```

Multipart route signature (required shape; aliases make the form part names camelCase and errors flow into `VALIDATION_ERROR`). For the idempotent replay, return `JSONResponse(status_code=200, content=ApiSuccess[SonicScanResult](data=stored_result).model_dump(mode="json"))`.

```python
# app/routers/assay.py — multipart route signature (required shape)
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.auth import CurrentUser, current_user
from app.core.errors import ApiError
from app.schemas import ApiSuccess, SonicScanForm, SonicScanResult

router = APIRouter(prefix="/api/v1/assay", tags=["assay"])
MAX_AUDIO_BYTES = 2 * 1024 * 1024


@router.post("/sonic-scans", status_code=201, response_model=ApiSuccess[SonicScanResult])
async def create_sonic_scan(
    audio: Annotated[UploadFile, File()],
    batch_id: Annotated[str, Form(alias="batchId")],
    stage: Annotated[str, Form()],
    mode: Annotated[str, Form()],
    client_scan_id: Annotated[str, Form(alias="clientScanId")],
    recorded_at: Annotated[str, Form(alias="recordedAt")],
    phone_model: Annotated[str | None, Form(alias="phoneModel")] = None,
    avg_fruit_mass_g: Annotated[str | None, Form(alias="avgFruitMassG")] = None,
    user: CurrentUser = Depends(current_user),
):
    try:  # validate form strings with the contract model; surface errors in the universal format
        form = SonicScanForm.model_validate({
            "batchId": batch_id, "stage": stage, "mode": mode, "clientScanId": client_scan_id,
            "recordedAt": recorded_at, "phoneModel": phone_model,
            "avgFruitMassG": float(avg_fruit_mass_g) if avg_fruit_mass_g not in (None, "") else None,
        })
    except (ValidationError, ValueError) as e:
        errs = e.errors() if isinstance(e, ValidationError) else [{"loc": ("avgFruitMassG",), "msg": str(e), "type": "float_parsing"}]
        raise RequestValidationError(errs)
    if audio.content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
        raise ApiError(415, "AUDIO_FORMAT_UNSUPPORTED", "Audio must be a 16-bit PCM mono WAV",
                       {"receivedContentType": audio.content_type})
    raw = await audio.read()
    if len(raw) > MAX_AUDIO_BYTES:
        raise ApiError(413, "AUDIO_TOO_LARGE", "Audio exceeds 2 MB", {"maxBytes": MAX_AUDIO_BYTES, "receivedBytes": len(raw)})
    # Remaining steps, in this order (Section 4.3.5):
    # 1. idempotency: if form.client_scan_id exists → return 200 with the stored scan + current batch
    # 2. permission + batch-state checks for form.stage → NOT_OWNER / FORBIDDEN_ROLE / BATCH_STATE_INVALID
    # 3. WAV validation + DSP pipeline (Section 4.3.4) → IMPACTS_NOT_DETECTED / SCAN_REJECTED_TAP_VARIATION
    # 4. persist scan + update batch (Section 4.3.5) → return 201 ApiSuccess(data=SonicScanResult(scan=scan_dto, batch=batch_dto))
    raise NotImplementedError
```

### 5.4 SQL (`schema.sql`, PostgreSQL dialect; also loads in SQLite)

```sql
-- FarmPool 360 x ChronoCrop — SQL schema (v1.1.0), PostgreSQL 15+ dialect.
-- SQLite demo: same DDL works (SQLite accepts these type names); see Section 5.4 type mapping.
-- All ids are UUID v4 generated by the application (uuid.uuid4()), never by the database.
-- All timestamps are UTC (TIMESTAMPTZ). Enum columns are VARCHAR + CHECK with exact enum values.

CREATE TABLE users (
    id                 UUID PRIMARY KEY,
    name               VARCHAR(80)  NOT NULL,
    phone              VARCHAR(16)  NOT NULL UNIQUE,
    password_hash      VARCHAR(255) NOT NULL,                       -- internal, never serialized
    role               VARCHAR(20)  NOT NULL CHECK (role IN ('FARMER','LOGISTICS','BUYER','ADMIN')),
    language           VARCHAR(2)   NOT NULL DEFAULT 'EN' CHECK (language IN ('EN','HI','MR','TA')),
    theme              VARCHAR(10)  NOT NULL DEFAULT 'SYSTEM' CHECK (theme IN ('LIGHT','DARK','SYSTEM')),
    organization_name  VARCHAR(120),
    home_latitude      DOUBLE PRECISION,
    home_longitude     DOUBLE PRECISION,
    created_at         TIMESTAMPTZ  NOT NULL
);

CREATE TABLE crop_profiles (
    id                              UUID PRIMARY KEY,
    crop_name                       VARCHAR(50) NOT NULL UNIQUE,
    display_name                    JSONB NOT NULL,                 -- LocalizedText
    ethylene_class                  VARCHAR(10) NOT NULL CHECK (ethylene_class IN ('EMITTER','SENSITIVE','NEUTRAL')),
    harvest_window_days_min         INTEGER NOT NULL,
    harvest_window_days_max         INTEGER NOT NULL,
    heat_stress_temp_c              DOUBLE PRECISION NOT NULL,
    typical_fruit_mass_g_min        DOUBLE PRECISION NOT NULL,
    typical_fruit_mass_g_max        DOUBLE PRECISION NOT NULL,
    stiffness_grade_a_min           DOUBLE PRECISION NOT NULL,
    stiffness_grade_b_min           DOUBLE PRECISION NOT NULL,
    defect_f0_max_hz                DOUBLE PRECISION NOT NULL,
    defect_tau_max_ms               DOUBLE PRECISION NOT NULL,
    rul_curve                       JSONB NOT NULL,                 -- RulCurvePoint[] (camelCase keys inside JSON)
    q10                             DOUBLE PRECISION NOT NULL DEFAULT 2.0,
    reference_temp_c                DOUBLE PRECISION NOT NULL DEFAULT 25.0,
    intake_stiffness_tolerance_pct  DOUBLE PRECISION NOT NULL DEFAULT 15.0,
    markdown_threshold_hours        DOUBLE PRECISION NOT NULL DEFAULT 24.0,
    default_markdown_pct            DOUBLE PRECISION NOT NULL DEFAULT 20.0,
    dispute_tolerance_hours         DOUBLE PRECISION NOT NULL DEFAULT 6.0,
    calibration_note                VARCHAR(500) NOT NULL DEFAULT '',
    updated_at                      TIMESTAMPTZ NOT NULL
);

CREATE TABLE harvest_advisories (
    id                          UUID PRIMARY KEY,
    farmer_id                   UUID NOT NULL REFERENCES users(id),
    crop_profile_id             UUID NOT NULL REFERENCES crop_profiles(id),
    days_since_flowering        INTEGER NOT NULL,
    target_pickup_date          TIMESTAMPTZ NOT NULL,
    latitude                    DOUBLE PRECISION NOT NULL,
    longitude                   DOUBLE PRECISION NOT NULL,
    maturity_fraction           DOUBLE PRECISION NOT NULL,
    hours_to_pickup             DOUBLE PRECISION NOT NULL,
    rain_prob_max_pct   DOUBLE PRECISION NOT NULL,
    rain_expected_in_hours      DOUBLE PRECISION,
    temp_max_c          DOUBLE PRECISION NOT NULL,
    humidity_mean_pct   DOUBLE PRECISION NOT NULL,
    vpd_max_kpa         DOUBLE PRECISION NOT NULL,
    weather_risk                VARCHAR(6)  NOT NULL CHECK (weather_risk IN ('LOW','MEDIUM','HIGH')),
    simulated                   BOOLEAN NOT NULL DEFAULT FALSE,
    recommendation              VARCHAR(20) NOT NULL CHECK (recommendation IN ('HARVEST_NOW','RECHECK_TOMORROW','WAIT_48H')),
    reason_code                 VARCHAR(30) NOT NULL CHECK (reason_code IN ('OVERMATURE','MATURE_WEATHER_RISK','MATURE_PICKUP_SOON','NEAR_MATURE_RECHECK','IMMATURE_WAIT')),
    confidence                  DOUBLE PRECISION NOT NULL,
    explanation                 TEXT NOT NULL,
    override_recommendation     VARCHAR(20) CHECK (override_recommendation IN ('HARVEST_NOW','RECHECK_TOMORROW','WAIT_48H')),
    override_reason             VARCHAR(500),
    overridden_by               UUID REFERENCES users(id),
    overridden_at               TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL
);

CREATE TABLE harvest_batches (
    id                       UUID PRIMARY KEY,
    farmer_id                UUID NOT NULL REFERENCES users(id),
    crop_profile_id          UUID NOT NULL REFERENCES crop_profiles(id),
    harvest_advisory_id      UUID REFERENCES harvest_advisories(id),
    weight_kg                DOUBLE PRECISION NOT NULL,
    avg_fruit_mass_g         DOUBLE PRECISION NOT NULL,
    harvested_at             TIMESTAMPTZ NOT NULL,
    pickup_latitude          DOUBLE PRECISION NOT NULL,
    pickup_longitude         DOUBLE PRECISION NOT NULL,
    status                   VARCHAR(20) NOT NULL DEFAULT 'PENDING_ASSAY' CHECK (status IN ('PENDING_ASSAY','GRADED','POOLED','IN_TRANSIT','ARRIVED')),
    quality_grade            VARCHAR(1) CHECK (quality_grade IN ('A','B','C')),
    internal_defect_flag     BOOLEAN NOT NULL DEFAULT FALSE,
    stiffness_index          DOUBLE PRECISION,
    loading_stiffness_index  DOUBLE PRECISION,
    initial_rul_hours        DOUBLE PRECISION,
    current_rul_hours        DOUBLE PRECISION,
    rul_updated_at           TIMESTAMPTZ,
    rul_at_dispatch_hours    DOUBLE PRECISION,
    created_at               TIMESTAMPTZ NOT NULL
);

CREATE TABLE acoustic_scans (                                       -- append-only: no UPDATE, no DELETE
    id                    UUID PRIMARY KEY,
    batch_id              UUID NOT NULL REFERENCES harvest_batches(id),
    stage                 VARCHAR(10) NOT NULL CHECK (stage IN ('FARM_GATE','LOADING','INTAKE')),
    mode                  VARCHAR(5)  NOT NULL CHECK (mode IN ('TAP','CHIRP')),
    client_scan_id        UUID NOT NULL UNIQUE,
    f0_hz                 DOUBLE PRECISION NOT NULL,
    tap_f0_values_hz      JSONB NOT NULL,                           -- number[]
    tap_variation_pct     DOUBLE PRECISION,
    spectral_centroid_hz  DOUBLE PRECISION NOT NULL,
    tau_ms                DOUBLE PRECISION NOT NULL,
    mfcc_mean             JSONB NOT NULL,                           -- number[13]
    avg_fruit_mass_g      DOUBLE PRECISION NOT NULL,
    stiffness_index       DOUBLE PRECISION NOT NULL,
    estimated_rul_hours   DOUBLE PRECISION NOT NULL,
    grade                 VARCHAR(1) NOT NULL CHECK (grade IN ('A','B','C')),
    internal_defect_flag  BOOLEAN NOT NULL,
    phone_model           VARCHAR(80),
    sample_rate_hz        INTEGER NOT NULL CHECK (sample_rate_hz IN (44100, 48000)),
    audio_path            TEXT NOT NULL,                            -- internal, never serialized
    scanned_by            UUID NOT NULL REFERENCES users(id),
    recorded_at           TIMESTAMPTZ NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL
);

CREATE TABLE transport_pools (
    id                       UUID PRIMARY KEY,
    carrier_id               UUID NOT NULL REFERENCES users(id),
    route_tier               VARCHAR(20) NOT NULL CHECK (route_tier IN ('FAST_QCOMM','FLEX_REGIONAL','STANDARD_WHOLESALE')),
    status                   VARCHAR(12) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_TRANSIT','ARRIVED')),
    origin_label             VARCHAR(100) NOT NULL,
    origin_latitude          DOUBLE PRECISION NOT NULL,
    origin_longitude         DOUBLE PRECISION NOT NULL,
    destination_name         VARCHAR(100) NOT NULL,
    destination_latitude     DOUBLE PRECISION NOT NULL,
    destination_longitude    DOUBLE PRECISION NOT NULL,
    max_capacity_kg          DOUBLE PRECISION NOT NULL,
    cohort_target_rul_hours  DOUBLE PRECISION,
    pickup_window_start      TIMESTAMPTZ NOT NULL,
    pickup_window_end        TIMESTAMPTZ NOT NULL,
    dispatched_at            TIMESTAMPTZ,
    arrived_at               TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL
);

CREATE TABLE pool_members (
    id           UUID PRIMARY KEY,
    pool_id      UUID NOT NULL REFERENCES transport_pools(id),
    batch_id     UUID NOT NULL UNIQUE REFERENCES harvest_batches(id),  -- a batch is in at most one pool
    kg_booked    DOUBLE PRECISION NOT NULL,
    reserved_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE telemetry_readings (                                   -- append-only
    id           UUID PRIMARY KEY,
    pool_id      UUID NOT NULL REFERENCES transport_pools(id),
    temp_c       DOUBLE PRECISION NOT NULL,
    latitude     DOUBLE PRECISION,
    longitude    DOUBLE PRECISION,
    recorded_at  TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE listings (
    id                UUID PRIMARY KEY,
    batch_id          UUID NOT NULL REFERENCES harvest_batches(id),
    farmer_id         UUID NOT NULL REFERENCES users(id),
    quantity_kg       DOUBLE PRECISION NOT NULL,
    available_kg      DOUBLE PRECISION NOT NULL,
    price_per_kg_inr  DOUBLE PRECISION NOT NULL,
    status            VARCHAR(10) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','SOLD_OUT','WITHDRAWN')),
    created_at        TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX uq_listings_one_active_per_batch ON listings (batch_id) WHERE status = 'ACTIVE';

CREATE TABLE buyer_orders (
    id                            UUID PRIMARY KEY,
    buyer_id                      UUID NOT NULL REFERENCES users(id),
    listing_id                    UUID NOT NULL REFERENCES listings(id),
    batch_id                      UUID NOT NULL REFERENCES harvest_batches(id),
    quantity_kg                   DOUBLE PRECISION NOT NULL,
    price_per_kg_inr              DOUBLE PRECISION NOT NULL,
    total_price_inr               DOUBLE PRECISION NOT NULL,
    guaranteed_arrival_rul_hours  DOUBLE PRECISION NOT NULL,
    status                        VARCHAR(16) NOT NULL DEFAULT 'PLACED' CHECK (status IN ('PLACED','INTAKE_ACCEPTED','INTAKE_FLAGGED')),
    intake_scan_id                UUID REFERENCES acoustic_scans(id),
    intake_result                 VARCHAR(8) CHECK (intake_result IN ('ACCEPTED','FLAGGED')),
    intake_stiffness_drop_pct     DOUBLE PRECISION,
    rul_at_intake_hours           DOUBLE PRECISION,
    storage_temp_c                DOUBLE PRECISION,
    intake_verified_at            TIMESTAMPTZ,
    markdown_pct                  DOUBLE PRECISION NOT NULL DEFAULT 0,
    markdown_triggered_at         TIMESTAMPTZ,
    created_at                    TIMESTAMPTZ NOT NULL
);

CREATE TABLE dispute_reports (
    id                         UUID PRIMARY KEY,
    order_id                   UUID NOT NULL UNIQUE REFERENCES buyer_orders(id),
    batch_id                   UUID NOT NULL REFERENCES harvest_batches(id),
    raised_by                  UUID NOT NULL REFERENCES users(id),
    raised_by_role             VARCHAR(20) NOT NULL CHECK (raised_by_role IN ('FARMER','LOGISTICS','BUYER','ADMIN')),
    description                VARCHAR(1000) NOT NULL,
    rul_farm_gate_hours        DOUBLE PRECISION NOT NULL,
    rul_loading_hours          DOUBLE PRECISION NOT NULL,
    rul_intake_hours           DOUBLE PRECISION NOT NULL,
    rul_shelf_hours            DOUBLE PRECISION NOT NULL,
    farm_gate_at               TIMESTAMPTZ NOT NULL,
    loading_at                 TIMESTAMPTZ NOT NULL,
    intake_at                  TIMESTAMPTZ NOT NULL,
    assessed_at                TIMESTAMPTZ NOT NULL,
    loading_checkpoint_source  VARCHAR(5) NOT NULL CHECK (loading_checkpoint_source IN ('SCAN','MODEL')),
    segments                   JSONB NOT NULL,                      -- DisputeSegment[] (camelCase keys inside JSON)
    responsible_party          VARCHAR(13) NOT NULL CHECK (responsible_party IN ('FARM','TRANSIT','BUYER_STORAGE','NONE')),
    created_at                 TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_batches_farmer      ON harvest_batches (farmer_id, created_at);
CREATE INDEX ix_scans_batch         ON acoustic_scans (batch_id, recorded_at);
CREATE INDEX ix_telemetry_pool      ON telemetry_readings (pool_id, recorded_at);
CREATE INDEX ix_orders_buyer        ON buyer_orders (buyer_id, created_at);
CREATE INDEX ix_listings_status     ON listings (status, created_at);
```

**SQLite / SQLAlchemy mapping.** Implement the ORM with SQLAlchemy 2.x using the portable types below so one codebase runs on both databases (`DATABASE_URL=sqlite:///./farmpool.db` for the demo, `postgresql+psycopg://user:password@localhost:5432/farmpool` for prod). SQLite drops time-zone info, so `UTCDateTime` re-attaches UTC on read; without it, `UtcDateTime` response fields would fail validation (naive datetime) and every list endpoint would 500. JSON columns store camelCase keys exactly as in the TS types (`rulCurve`, `segments`, `displayName`). Create tables with `Base.metadata.create_all()` at startup (no migrations needed for the hackathon); the DDL above is the reference the ORM must match column-for-column.

| DDL type | SQLAlchemy type | SQLite storage |
|---|---|---|
| `UUID` | `Uuid(as_uuid=True)` | CHAR(32) |
| `TIMESTAMPTZ` | `UTCDateTime` (below) | text, re-tagged UTC on read |
| `JSONB` | `JSON().with_variant(JSONB(), "postgresql")` | text JSON |
| `DOUBLE PRECISION` | `Float` | REAL |
| `BOOLEAN` | `Boolean` | INTEGER 0/1 |
| `VARCHAR(n)` + `CHECK` | `String(n)` + `CheckConstraint` | TEXT |

```python
# app/db/types.py — portable column types for PostgreSQL and SQLite (SQLAlchemy 2.x)
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import JSONB


class UTCDateTime(TypeDecorator):
    """Stores UTC; always returns timezone-aware UTC datetimes (SQLite drops tzinfo otherwise)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to the database; use datetime.now(timezone.utc)")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


UUIDType = Uuid(as_uuid=True)                       # UUID on Postgres, CHAR(32) on SQLite
JSONType = JSON().with_variant(JSONB(), "postgresql")
```


---

## 6. AI GENERATION DIRECTIVES

### 6.1 Both AIs

1. **"If anything is ambiguous, follow the contract literally and list the ambiguity at the end instead of guessing."**
2. Sections 2–5 are binding. Do not add, rename, remove or re-type any route, query param, form field, JSON key or enum value. Section 6.6 lists every decision already taken on points the v1.0 PRD left open; do not reopen them.
3. Out of scope means absent: no image upload, camera capture, crop recognition, mass estimation, sowing planner, payment flow, or milk / sealed-pack testing anywhere in UI, API or database.
4. The contract version is `1.1.0`. Backend returns it in `GET /health`; frontend shows a warning banner if the major.minor differs from its own `CONTRACT_VERSION = "1.1.0"`.

### 6.2 v0 (Next.js frontend)

1. **"Use the TypeScript interfaces strictly for component mock data. Do not invent new fields. Mock error states must use the universal error format."**
2. Create `lib/api/types.ts` from Section 5.2 verbatim and `lib/api/client.ts` from the code below verbatim. `client.ts` is the only file that calls `fetch`. Every data call is `api("<METHOD> <path>", { params, query, body })`, which type-checks path params, query and body against `ApiRoutes`. No `any`, no `as unknown as`, no hand-written response types.
3. **Mocks:** build `lib/api/mock.ts` that calls `setMockHandler(...)` when `NEXT_PUBLIC_USE_MOCKS === "true"`. Each fixture is typed as `ApiRoutes[K]["res"]`, uses valid lowercase UUID v4 strings and `YYYY-MM-DDTHH:MM:SSZ` datetimes, and covers every enum value somewhere. Error fixtures throw `new ApiError(status, code, message, details)` with a real `ErrorCode` and the `details` keys from Section 3.2 (include at least `VALIDATION_ERROR` with `fields`, `POOL_INCOMPATIBLE`, `SCAN_REJECTED_TAP_VARIATION`, `TOKEN_EXPIRED`). Switching mocks off must require no component change.
4. **Routes and guards:** implement exactly the routes in Section 1.3. After login call `GET /users/me`; redirect each role to its home (`/farmer`, `/logistics`, `/buyer/marketplace`, `/admin/crop-profiles`); block routes for other roles client-side. On `ApiError.status === 401` redirect to `/login?next=…`.
5. **Forms:** mirror the constraints in the TS doc comments (lengths, ranges, regex). Send `null` explicitly for nullable fields; never omit them (Rule 16). Show `VALIDATION_ERROR.details.fields[].message` under the input whose name equals `field`. Warn (do not block) when `avgFruitMassG` is outside the crop's `typicalFruitMassGMin–Max`.
6. **i18n:** dictionaries `en`, `hi`, `mr`, `ta` with keys for every enum value (`enum.<EnumName>.<VALUE>`), every error code (`error.<CODE>`), and the five advisory templates (`advisory.<REASON_CODE>`, same placeholders as Section 4.3.3). Language comes from `user.language`; changing it calls `PATCH /users/me {language}`. Crop names use `cropProfile.displayName[lang]` (keys `en`/`hi`/`mr`/`ta`). Format dates with `Intl.DateTimeFormat` using `EN→en-IN`, `HI→hi-IN`, `MR→mr-IN`, `TA→ta-IN`.
7. **Theme:** Tailwind `darkMode: "class"`; `user.theme` `LIGHT`/`DARK`/`SYSTEM`; high-contrast palette readable in sunlight; touch targets ≥ 44 px.
8. **SonicAssay recorder:**
   - `navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } })`; `new AudioContext({ sampleRate: 44100 })`. If `audioContext.sampleRate` is not 44100 or 48000, show "Unsupported device audio rate" and stop.
   - Capture raw Float32 samples with an `AudioWorkletNode` (fallback `ScriptProcessorNode`); feed an `AnalyserNode` (fftSize 2048) for the live spectrogram canvas.
   - Flow: "Stay quiet" countdown 1.5 s → prompts "Tap 1", "Tap 2", "Tap 3" (stop at 8 s total). CHIRP: after the 1.5 s silence play a 1.5 s `OscillatorNode` sweep 100→2500 Hz (`linearRampToValueAtTime`), record 1.5 s more.
   - Encode with `encodeWav(samples, audioContext.sampleRate)`, build the body with `buildSonicScanForm`, `clientScanId = crypto.randomUUID()` generated when recording starts.
   - On `SCAN_REJECTED_TAP_VARIATION` / `IMPACTS_NOT_DETECTED`, show the re-tap screen with the returned `tapF0ValuesHz`.
9. **Offline queue (PWA):** IndexedDB store `pendingScans` keyed by `clientScanId` holding `{ batchId, stage, mode, recordedAt, phoneModel, avgFruitMassG, wav: Blob, queuedAt }`. Enqueue when `navigator.onLine === false` or the upload throws `NETWORK_ERROR`. Replay oldest-first on the `online` event and on app start. Delete the entry on any 2xx or any 4xx except 401; keep it on `NETWORK_ERROR`, 5xx and 401 (replay after re-login). Show a "Queued (n)" badge. Server idempotency makes replays safe. Service worker caches the app shell only; never cache `/api/` responses.
10. **QR:** render `batch.qrCodeValue` with `qrcode.react` (`QRCodeSVG`). `/passport/[batchId]` is public and works without login; it shows grade, RUL gauge, the scans timeline (FARM_GATE → LOADING → INTAKE) and a temperature chart from `telemetry`.
11. **Demo helpers (UI only):** "Simulate rain in 30 h" toggle sends `simulateRainInHours: 30`; logistics "Simulate trip" button posts telemetry readings with `recordedAt` stepping forward 1 h from `max(last recordedAt, dispatchedAt)`; buyer "Fast-forward shelf" slider sends `simulateHoursAhead`. FEFT-vs-FIFO panel: sort pool members by `currentRulHours` (FEFT) vs `reservedAt` (FIFO) and show which batches would breach 24 h.

```ts
// lib/api/client.ts — the ONLY place the frontend calls fetch (required, copy as-is)
import type { ApiRoutes, ApiRouteKey, ApiResponse, ClientErrorCode, ScanMode, ScanStage, SonicScanResult, UUID } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "fp_access_token";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: ClientErrorCode,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

export const tokenStore = {
  get: (): string | null => {
    try { return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set: (t: string): void => { try { window.localStorage.setItem(TOKEN_KEY, t); } catch { /* storage unavailable */ } },
  clear: (): void => { try { window.localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } },
};

type ParamNames<K extends string> = K extends `${string}:${infer P}/${infer Rest}`
  ? P | ParamNames<`/${Rest}`>
  : K extends `${string}:${infer P}` ? P : never;
type PathParams<K extends string> = [ParamNames<K>] extends [never] ? Record<string, never> : Record<ParamNames<K>, string>;

export type CallArgs<K extends ApiRouteKey> = {
  params?: PathParams<K>;
  query?: ApiRoutes[K]["query"] extends null ? undefined : ApiRoutes[K]["query"];
  body?: ApiRoutes[K]["body"] extends null ? undefined : ApiRoutes[K]["body"] extends "multipart" ? FormData : ApiRoutes[K]["body"];
};

/** Mock mode (NEXT_PUBLIC_USE_MOCKS=true): lib/api/mock.ts registers a handler that returns typed fixtures
 *  or throws ApiError with a real ErrorCode. Components never know whether mocks are on. */
export type MockHandler = <K extends ApiRouteKey>(key: K, args: CallArgs<K>) => Promise<ApiRoutes[K]["res"]>;
let mockHandler: MockHandler | null = null;
export function setMockHandler(handler: MockHandler | null): void { mockHandler = handler; }

/** Typed call: api("POST /pools/:poolId/reservations", { params: { poolId }, body: { batchId } }) */
export async function api<K extends ApiRouteKey>(key: K, args: CallArgs<K> = {}): Promise<ApiRoutes[K]["res"]> {
  if (mockHandler && process.env.NEXT_PUBLIC_USE_MOCKS === "true") return mockHandler(key, args);
  const [method, template] = key.split(" ") as [string, string];
  let path = template;
  for (const [k, v] of Object.entries((args.params ?? {}) as Record<string, string>)) path = path.replace(`:${k}`, encodeURIComponent(v));
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries((args.query ?? {}) as Record<string, unknown>)) if (v !== undefined && v !== null) qs.set(k, String(v));
  const url = `${API_BASE_URL}/api/v1${path}${qs.toString() ? `?${qs}` : ""}`;

  const headers = new Headers();
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body: BodyInit | undefined;
  if (args.body instanceof FormData) body = args.body; // browser sets multipart boundary itself
  else if (args.body !== undefined) { headers.set("Content-Type", "application/json"); body = JSON.stringify(args.body); }

  let res: Response;
  try { res = await fetch(url, { method, headers, body }); }
  catch { throw new ApiError(0, "NETWORK_ERROR", "Cannot reach the server. Check your connection."); }

  let json: ApiResponse<ApiRoutes[K]["res"]>;
  try { json = (await res.json()) as ApiResponse<ApiRoutes[K]["res"]>; }
  catch { throw new ApiError(res.status, "INVALID_RESPONSE", "Server returned a non-JSON response."); }

  if (json.success) return json.data;
  if (res.status === 401) tokenStore.clear();
  throw new ApiError(res.status, json.error.code, json.error.message, json.error.details);
}

/** Builds the multipart body for POST /assay/sonic-scans. Omit optional fields instead of sending "null". */
export function buildSonicScanForm(input: {
  wav: Blob; batchId: UUID; stage: ScanStage; mode: ScanMode; clientScanId: UUID; recordedAt: string;
  phoneModel: string | null; avgFruitMassG: number | null;
}): FormData {
  const fd = new FormData();
  fd.append("audio", input.wav, "scan.wav");
  fd.append("batchId", input.batchId);
  fd.append("stage", input.stage);
  fd.append("mode", input.mode);
  fd.append("clientScanId", input.clientScanId);
  fd.append("recordedAt", input.recordedAt);
  if (input.phoneModel !== null) fd.append("phoneModel", input.phoneModel);
  if (input.avgFruitMassG !== null) fd.append("avgFruitMassG", String(input.avgFruitMassG));
  return fd;
}

/** 16-bit PCM mono WAV encoder for Float32 samples captured via AudioWorklet. Never upload MediaRecorder webm/mp4. */
export function encodeWav(samples: Float32Array, sampleRate: 44100 | 48000): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sampleRate, true); v.setUint32(28, sampleRate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  w(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) { const s = Math.max(-1, Math.min(1, samples[i])); v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true); }
  return new Blob([buf], { type: "audio/wav" });
}

/** Example (type-checks): */
export async function uploadScan(wav: Blob, batchId: UUID): Promise<SonicScanResult> {
  return api("POST /assay/sonic-scans", {
    body: buildSonicScanForm({ wav, batchId, stage: "FARM_GATE", mode: "TAP", clientScanId: crypto.randomUUID(),
      recordedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"), phoneModel: null, avgFruitMassG: null }),
  });
}
```

### 6.3 Backend AI (Claude Code, FastAPI)

1. **"Implement CORS middleware allowing http://localhost:3000 and http://127.0.0.1:3000 with the Authorization header. Strictly adhere to the Pydantic schemas, the success envelope and the Universal Error Format. Do not add routes or fields outside the contract."** (FastAPI's own `/docs` and `/openapi.json` may stay enabled in development; they are not part of the contract.)
2. **Stack:** Python ≥ 3.11; `fastapi>=0.115`, `pydantic>=2.11,<3`, `sqlalchemy>=2.0`, `uvicorn[standard]`, `python-multipart`, `pyjwt`, `bcrypt`, `httpx`, `numpy`, `scipy`, `librosa`, `pytest`. Decode WAV with the stdlib `wave` module (PCM 16-bit only).
3. **Layout:** `app/main.py`, `app/core/{config,errors,auth}.py`, `app/schemas.py`, `app/db/{types,models,session}.py`, `app/routers/{health,auth,users,crop_profiles,advisories,batches,passport,assay,pools,listings,orders,intake,disputes}.py`, `app/services/{weather,dsp,grading,pooling,decay,markdown,disputes}.py`, `app/seed.py`, `tests/`.
4. **Every route** declares `response_model=ApiSuccess[<Type>]` (or `ApiSuccess[Paginated[<Type>]]`) and `status_code` exactly as in Section 4.2, and returns `ApiSuccess(data=...)`. Contract errors use `ApiError`; never return a bare dict or raise `HTTPException`. Create the app with `FastAPI(title="FarmPool 360 API", version="1.1.0", redirect_slashes=False)`.
5. **Copy verbatim:** Section 5.3 → `app/schemas.py`; 3.3 → `app/core/errors.py`; 3.4 → `app/core/auth.py`; the `db_types` block in 5.4 → `app/db/types.py`. Build ORM models column-for-column from 5.4 using those types.
6. **Env vars:** `DATABASE_URL` (default `sqlite:///./farmpool.db`), `JWT_SECRET` (≥ 32 chars; dev default allowed only when `ENV=dev`), `FRONTEND_BASE_URL` (default `http://localhost:3000`), `CORS_EXTRA_ORIGINS` (comma-separated, default empty), `AUDIO_DIR` (default `./data/audio`), `SEED_DEMO` (default `true`), `ENV` (default `dev`).
7. **Cursor pagination:** cursor = URL-safe base64 of `"<createdAt ISO>|<id>"` (telemetry: `recordedAt`); fetch `limit + 1` rows to decide `nextCursor`. An undecodable cursor is `VALIDATION_ERROR` on field `cursor`.
8. **Rounding** per Rule 14 when building response DTOs; never round stored values.
9. **Tests (pytest + TestClient):** one happy-path test per route asserting `success: true` and that `response.json()["data"]` validates against the route's Pydantic type; plus error tests for 401 (no token), 403 (wrong role), 422 (unknown field), and every domain error in Section 3.2. Include a synthetic WAV fixture: 1.5 s of low noise followed by three 40 ms decaying 400 Hz sine bursts 0.6 s apart, 4 s total, 44 100 Hz (expect f0 ≈ 400 Hz, variation < 12 %), and one with bursts at 300/400/520 Hz (expect `SCAN_REJECTED_TAP_VARIATION`).
10. Log every simulated markdown webhook payload at INFO level as JSON.

### 6.4 Seed data (backend inserts on startup when `SEED_DEMO=true` and the `users` table is empty)

**Users** (password for all: `Demo@12345`):

| name | phone | role | language | organizationName | home lat, lng |
|---|---|---|---|---|---|
| Ramesh Pawar | `+919800000001` | FARMER | HI | Pimpalgaon Tomato FPO | 20.166700, 73.983300 |
| Sunita Logistics | `+919800000002` | LOGISTICS | EN | Sahyadri Reefer Lines | 20.011000, 73.790000 |
| Arjun Mehta | `+919800000003` | BUYER | EN | Nashik Road Dark Store 4 | 19.954800, 73.837000 |
| Dr. Kavita Rao | `+919800000004` | ADMIN | EN | FarmPool Agronomy | null, null |

**Crop profiles** (calibration values are **placeholders** until replaced with your own labelled recordings; `calibrationNote` = "Placeholder calibration — replace with hackathon validation data"; all use `markdownThresholdHours` 24, `defaultMarkdownPct` 20, `disputeToleranceHours` 6, `referenceTempC` 25):

| cropName | displayName en / hi / mr / ta | ethylene | harvest days min–max | heat °C | mass g min–max | grade A min | grade B min | defect f0 < Hz & τ < ms | q10 | intake tol % | rulCurve (stiffnessIndex → rulHours) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `TOMATO` | Tomato / टमाटर / टोमॅटो / தக்காளி | EMITTER | 40–55 | 35 | 80–200 | 3 500 000 | 2 000 000 | 220 & 6.0 | 2.5 | 15 | 1 000 000→24, 2 000 000→60, 3 000 000→110, 4 500 000→160 |
| `MANGO` | Mango / आम / आंबा / மாம்பழம் | EMITTER | 90–120 | 38 | 180–350 | 2 000 000 | 1 200 000 | 140 & 5.0 | 2.2 | 15 | 600 000→24, 1 200 000→72, 2 000 000→120, 3 000 000→168 |
| `CUCUMBER` | Cucumber / खीरा / काकडी / வெள்ளரிக்காய் | SENSITIVE | 10–18 | 35 | 150–400 | 5 000 000 | 3 000 000 | 250 & 5.0 | 2.0 | 15 | 2 000 000→24, 3 000 000→60, 5 000 000→120, 7 000 000→168 |
| `WATERMELON` | Watermelon / तरबूज / कलिंगड / தர்பூசணி | SENSITIVE | 30–40 | 38 | 3 000–8 000 | 6 000 000 | 4 000 000 | 100 & 8.0 | 2.0 | 15 | 3 000 000→48, 4 000 000→120, 6 000 000→240, 8 000 000→336 |
| `POMEGRANATE` | Pomegranate / अनार / डाळिंब / மாதுளை | NEUTRAL | 120–150 | 40 | 200–400 | 3 500 000 | 2 200 000 | 180 & 5.0 | 2.0 | 15 | 1 500 000→72, 2 200 000→168, 3 500 000→336, 5 000 000→480 |

**Pools** (carrier = Sunita Logistics, origin "Pimpalgaon cluster" 20.166700, 73.983300, capacity 4 000 kg, pickup window seed time + 12 h → + 36 h):

| routeTier | destinationName | destination lat, lng |
|---|---|---|
| `FAST_QCOMM` | Nashik Road Dark Store 4 | 19.954800, 73.837000 |
| `FLEX_REGIONAL` | Vashi APMC, Navi Mumbai | 19.079000, 73.009000 |
| `STANDARD_WHOLESALE` | Ahmedabad Jamalpur Market | 23.017000, 72.587000 |

### 6.5 Integration smoke test (run before connecting; both sides must pass it unchanged)

Run against the real backend with the seed data. Each step names the expected status and `data` type.

1. `GET /health` → 200 `HealthStatus`, `version: "1.1.0"`.
2. `POST /auth/login` farmer → 200 `AuthResponse`. Repeat for logistics and buyer; keep three tokens.
3. `GET /crop-profiles` → 200, 5 items; pick `TOMATO`.
4. `POST /harvest-advisories` with `simulateRainInHours: 30`, `daysSinceFlowering: 48` → 201, `recommendation: "HARVEST_NOW"`, `reasonCode: "MATURE_WEATHER_RISK"`.
5. `POST /batches` (500 kg, 150 g, pickup 20.17, 73.98) → 201, `status: "PENDING_ASSAY"`, `qrCodeValue` ends with `/passport/<id>`.
6. `POST /assay/sonic-scans` FARM_GATE with the synthetic 400 Hz WAV → 201; batch `GRADED`; resend the same `clientScanId` → 200 with the same `scan.id`.
7. `POST /pools/match` → 200; `requiredRouteTier` consistent with `batchRulHours`; reserve the top match → 201 `PoolMember`; batch `POOLED`.
8. `POST /listings` (200 kg at 24 INR) → 201; buyer `GET /listings?minArrivalRulHours=0` contains it; buyer `POST /orders` 100 kg → 201, `totalPriceInr: 2400`.
9. Logistics: `POST /pools/{id}/dispatch` → 200 `IN_TRANSIT`; `POST /pools/{id}/telemetry` twice with increasing `recordedAt` (25 °C then 35 °C) → 201 each, RUL decreasing; then `POST /pools/{id}/arrive` → 200 `ARRIVED`.
10. Buyer: INTAKE scan → 201; `POST /intake/verify` with `storageTempC: 25` → 200 `ACCEPTED` or `FLAGGED`; `POST /orders/{id}/markdown-check` with `simulateHoursAhead: 200` → 200 `newlyTriggered: true`, `webhookPayload.event: "FLASH_MARKDOWN"`.
11. `POST /disputes` → 201 with 3 `segments` in order `FARM`, `TRANSIT`, `BUYER_STORAGE`; repeat → 409 `DISPUTE_ALREADY_EXISTS`.
12. Negative checks: no token on `GET /users/me` → 401 `AUTH_REQUIRED`; buyer `POST /pools` → 403 `FORBIDDEN_ROLE`; `POST /batches` with an extra key → 422 `VALIDATION_ERROR`; any 500 response still carries `Access-Control-Allow-Origin` for `http://localhost:3000`.

### 6.6 Decisions taken in v1.1 (ambiguities in v1.0, now closed)

| # | v1.0 issue | v1.1 decision |
|---|---|---|
| D1 | Integer `SERIAL` ids and `VARCHAR` QR ids | UUID v4 strings for every entity; QR encodes the passport URL of the batch id |
| D2 | Only 8 endpoints, no request/response shapes | 40 routes with exact payloads (Section 4.2), mirrored by the typed `ApiRoutes` map |
| D3 | No auth, envelope or error format | Rules 9–10, 19–21 and Section 3 |
| D4 | FEFT gap: RUL 60–120 h had no route | Third tier `FLEX_REGIONAL` (4.3.6) |
| D5 | HarvestWindow rules left cases undefined (mature + clear weather, pickup date unused) | Ordered rule table R1–R5 with confidence and templates (4.3.3) |
| D6 | Requests keyed by `cropName` | Requests use `cropProfileId` (UUID); responses also carry `cropName` for display |
| D7 | QR "minted on scan" but scan needs a batch | Batch is created first (`POST /batches`); QR exists from creation; scans attach to it |
| D8 | Intake spot-check needed audio but verify was JSON | Spot-check uses the same multipart scan endpoint with `stage: INTAKE`; verify takes the `scanId` |
| D9 | DSP both in browser and server | Server DSP is authoritative; browser FFT is display-only; offline queue stores the WAV |
| D10 | `PATCH` telemetry + hourly job | `POST` telemetry; RUL updates per reading with Q10; no background job |
| D11 | Location as "pincode or GPS" | Latitude/longitude only (GPS or profile home location) |
| D12 | "Pre-book pool slot" without a batch | UI navigation to batch creation; no draft reservation |
| D13 | Browser MediaRecorder output is webm/mp4, not WAV | Frontend encodes 16-bit PCM WAV from raw samples (`encodeWav`) |
| D14 | `to_camel` turns `next_48h` into `next48H` | Field naming rule 7; weather fields renamed (`rainProbMaxPct`, `tempMaxC`, …) with the 48 h window documented |
| D15 | Exception handler 500s lose CORS headers; `HTTPBearer` may return 403 for missing token | Middleware-based catch-all and `HTTPBearer(auto_error=False)` (Sections 3.3, 3.4) |
| D16 | SQLite returns naive datetimes | `UTCDateTime` column type (Section 5.4) |
| D17 | Dispute attribution undefined | Checkpoint/segment algorithm with expected vs excess loss (4.3.10) |
| D18 | Order linked to both pool and batch | Order links to listing and batch; the pool is reached through the batch |
| D19 | Localised explanations from the backend | Backend sends English + `reasonCode`; UI localises |


---

## Consistency Check

Verified mechanically on the exact code blocks in this file (TypeScript 5.6 `tsc --strict`, Python 3.13 + Pydantic 2.13, FastAPI 0.16x TestClient, SQLite 3), not by reading alone.

| Check | Result |
|---|---|
| Every endpoint in 4.2 appears in `ApiRoutes` (5.2) and vice versa | ✅ 40 / 40, same methods and paths |
| Every endpoint used in the screen map (1.3) exists in 4.2 | ✅ |
| Every payload and response in 4.2 maps to a defined schema in both TS and Pydantic | ✅ 50 TS interfaces ↔ 50 Pydantic models (+ `SonicScanForm` for the multipart fields, + `CamelModel` base) |
| Field names identical after `to_camel` for every model | ✅ no TS-only or Python-only fields |
| Nullability identical (`T \| null` ↔ `T \| None`, both required) | ✅ only `UpdateProfileRequest` uses omittable keys, on both sides |
| No digit-letter camelCase traps (`48H`, `F0S`) | ✅ |
| Every enum identical in TS, Python and SQL `CHECK` lists | ✅ 20 enums; Python member name == value |
| SQL columns = Pydantic fields − computed fields + internal columns | ✅ 11 tables; DDL loads in SQLite |
| TypeScript client rejects wrong body keys and wrong path-param names at compile time | ✅ |
| Error wiring returns the universal format for 401 / 403 / 404 / 405 / 415 / 422 / 500, and 500s keep CORS headers | ✅ |
| Multipart form fields validate with camelCase names and naive datetimes are rejected | ✅ |
| SQLite round-trip returns timezone-aware UTC datetimes | ✅ |
| Worked examples in 4.4 validate against their Pydantic models | ✅ |
| DSP spec (4.3.4) recovers f0 ≈ 398 Hz and τ ≈ 8 ms on the synthetic 400 Hz test WAV and rejects the 300/400/520 Hz WAV (CV 22 %) | ✅ |
| Every field is camelCase in JSON | ✅ |
| No out-of-scope field or route (images, crop recognition, mass estimation, sowing, payments, milk/sealed packs) | ✅ |
| No placeholders (`TBD`, `etc.`, `...`) in Sections 4 and 5 | ✅ |

**Open items that need your data, not code:** replace the placeholder crop calibration (Section 6.4) with your own labelled recordings, and have the HarvestWindow thresholds (4.3.3) reviewed by an agronomist before quoting accuracy.
