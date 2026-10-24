# FarmPool 360 × ChronoCrop

A Next.js App Router frontend inspired by the project PRD and the supplied farm dashboard reference. Local fonts, an original farm landscape, responsive layouts, dark mode, and English/Hindi/Marathi/Tamil navigation are included.

## Run

Use the existing checkout; cloud tasks are already isolated and do not require a worktree.

```bash
cd /workspace/snack-overflow
python3 -m venv /workspace/.snack-overflow-venv
/workspace/.snack-overflow-venv/bin/python -m pip install -r requirements.txt
cd frontend
npm ci
cd ..
bash scripts/dev.sh
```

Requires Node.js 20.9+ and Python 3.11+. Frontend listens on port 3000; FastAPI on port 8000. The frontend proxies `/api/v1/*` to FastAPI, so both work on the same origin. Override `NEXT_PUBLIC_API_BASE_URL` only for an externally hosted backend. `FARMPOOL_VENV` and `FARMPOOL_RUNTIME` override the script's local environment/data directories.

The runtime uses a separate SQLite database and audio directory under `/workspace/.snack-overflow-runtime`; the checked-in database and Windows `.venv` are preserved.

## Present

The app opens directly into **Presentation mode**, labeled throughout. Sample harvests, shared rides, marketplace listings, and completed demo interactions persist in the current browser. No backend is needed for this mode.

Suggested demo:

1. Dashboard → **Harvest window** → calculate a recommendation; toggle rain and calculate again.
2. **My harvest** → add a crop batch.
3. **Quality scan** → choose the batch → **Try a demo scan**.
4. Open the **Bio-Clock passport**, including its QR code and quality journey.
5. **Shared transport** → choose the graded batch → **Find my match** → reserve a ride.
6. **Marketplace** → list the harvest.
7. **Settings & help** → switch to Buyer → order produce → view Orders.
8. Switch to Logistics to create a pool and demonstrate dispatch/arrival.

Use **Settings & help → Reset presentation data** before your pitch. A demo passport is a browser-local sample; use live mode to share a public passport across devices.

## Connect the backend

Choose **Connect live account**. The login form prefills the seeded farmer. Seeded demo password: `Demo@12345`.

| Role | Phone |
|---|---|
| Farmer | +919800000001 |
| Logistics | +919800000002 |
| Buyer | +919800000003 |
| Agronomist | +919800000004 |

Live requests use the PRD's typed client and API contract. Login, registration, crop profiles, batch creation, harvest recommendations, WAV scan uploads, public passports, pool matching/reservations, pool creation/dispatch/arrival, listings, orders, and profile preferences connect to existing backend endpoints. Microphone capture needs browser permission and a secure context; WAV upload is the alternative. Weather forecasts need access to `api.open-meteo.com`; the existing backend has its own baseline fallback.

This is a hackathon presentation implementation, not full PRD production parity. Full translation of page copy, offline scan synchronization/PWA, admin calibration editing, telemetry entry, buyer intake verification, dispute forms, and advanced route-specific permissions are not implemented. The backend remains the authority for authorization and acoustic results. Demo scans are simulated and clearly labeled. Demo stock and route matches illustrate the journey and do not implement the backend's complete compatibility or ledger rules.

## Validate

```bash
cd frontend
npm run typecheck
npm run build
```

Production: run `npm run build` once, then `npm start`. Start FastAPI separately with `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`, supplying `DATABASE_URL` and `AUDIO_DIR` as in `scripts/dev.sh`.
