# 🌱 FarmPool 360 × ChronoCrop

> **Intelligent Post-Harvest Cold-Chain Logistics, Non-Invasive Acoustic Quality Assay & Spoilage Prevention for Smallholder Farmers.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel%20Monorepo-000000?logo=vercel&logoColor=white)](https://vercel.com/)

---

## 📌 Executive Summary

Up to **40% of fresh horticultural produce** in developing agricultural supply chains is lost between harvest and retail. Smallholder farmers lack access to expensive testing spectrometers, reliable refrigerated transport, and predictive harvest timing. 

**FarmPool 360 × ChronoCrop** bridges this gap by turning ordinary smartphones into non-invasive diagnostic tools and aggregating farm harvests into optimized, shared cold-chain transport corridors:

1. **ChronoCrop Acoustic Assay:** A smartphone-based acoustic resonance AI that grades fruit maturity and estimates Remaining Useful Life (RUL in hours) by listening to knuckle/spatula taps.
2. **Prescriptive Harvest Advisory:** Hyperlocal 48-hour climate forecasting coupled with crop maturity models to advise farmers exactly when to harvest (`HARVEST_NOW` vs. `WAIT_48H`).
3. **FarmPool Shared Cold Chain:** A multi-constraint logistics engine that pools smallholder batches into refrigerated trucks based on geographic proximity, shelf-life cohorts, and ethylene gas biochemical compatibility.
4. **$Q_{10}$ Dynamic Bio-Clock Passport:** Real-time biophysical decay tracking across the supply chain, backed by QR verification and automated cold-chain breach attribution.

---

## 🛠️ Complete Tech Stack

| Domain | Technology / Library | Purpose |
| :--- | :--- | :--- |
| **Frontend** | **Next.js 15 (App Router)** + **React 19** | Modern, responsive UI with server & client components |
| **Language** | **TypeScript 5.9** | Strict end-to-end typing matching backend DTO schemas |
| **Audio Capture** | **Web Audio API (`AudioWorklet`)** | Records 16-bit PCM mono WAV directly from phone microphone |
| **Backend API** | **FastAPI** (Python 3.11+) + **Uvicorn** | High-throughput asynchronous REST API |
| **Data Validation** | **Pydantic v2** | Strict Universal Error envelopes & DTO contract enforcement |
| **ORM & Database** | **SQLAlchemy 2.0** + **SQLite / PostgreSQL** | Relational data persistence with UUID primary keys |
| **Signal Processing / AI** | **`librosa`**, **`scipy`**, **`numpy`** | Spectral FFT, $f_0$ fundamental resonance extraction |
| **Thermodynamics** | **Biochemical $Q_{10}$ Kinetic Model** | Temperature-dependent Remaining Useful Life (RUL) tracking |
| **Security & Auth** | **PyJWT** + **Passlib (Bcrypt)** | Stateless role-based access control (Farmer, Logistics, Buyer, Admin) |
| **External APIs** | **Open-Meteo API** | Free, zero-key 48-hour hourly weather forecasting |
| **Deployment** | **Vercel** (`vercel.json` Multi-Service) | Unified monorepo deployment with internal service bindings |

---

## 🧠 Key Algorithmic Innovations

### 1. 🎵 Acoustic Resonance Assay (DSP & Spectral ML)
- **Input:** 16-bit PCM Mono audio (44.1 kHz) recorded via smartphone mic.
- **Processing:** Isolates tap events from background ambient noise using Short-Time Fourier Transform (STFT) via `scipy.signal` and `librosa`.
- **Validation:** Measures peak fundamental frequency ($f_0$) across multiple taps; rejects scans if frequency variance exceeds **12%** (`SCAN_REJECTED_TAP_VARIATION`).
- **Firmness Grading:** Maps resonance frequency against cultivar-specific reference thresholds to grade produce (`GRADE_A`, `GRADE_B`, `GRADE_C`) and initialize baseline RUL.

### 2. 🚚 Multi-Constraint Vehicle Pooling Algorithm
- **Geospatial Distance:** Evaluates pickup clusters within a **20 km radius** using the **Haversine formula**.
- **Compatibility Matrix:**
  - **Ethylene Separation:** Strictly prevents ethylene-emitting crops (e.g., bananas) from sharing pools with ethylene-sensitive crops (e.g., tomatoes/greens).
  - **RUL Cohort Synchronization:** Enforces that co-loaded batches have matching shelf-life profiles within a **$\pm 24\text{h}$ window**.
  - **Thermal & Route Tiers:** Automatically assigns reefer vs. ambient vehicles based on batch urgency.
- **Match Scoring:**
  $$\text{Match Score} = 1.0 - \left(0.5 \times \frac{\text{Distance}}{20\text{ km}} + 0.5 \times \frac{|\Delta \text{RUL}|}{24\text{ hours}}\right)$$

### 3. 🌡️ Biophysical $Q_{10}$ Temperature Decay Model
Produce spoilage rate increases exponentially with temperature fluctuations during transit:
$$\text{Decay Factor} = Q_{10}^{\frac{T_{\text{transit}} - T_{\text{reference}}}{10}}$$
$$\text{Consumed Shelf-Life (h)} = \Delta t \times \text{Decay Factor}$$
Every temperature telemetry log updates the batch's Bio-Clock passport in real-time, preventing dispute ambiguity.

---

## 📂 Repository Layout

```text
snack-overflow/
├── app/                        # FastAPI Backend Application
│   ├── core/                   # Auth guards, configs, error handlers
│   ├── db/                     # SQLAlchemy models, session, column types
│   ├── routers/                # 13 REST API routers (38 endpoints)
│   │   ├── advisories.py       # Harvest recommendations
│   │   ├── assay.py            # Acoustic WAV upload & analysis
│   │   ├── auth.py             # User registration & JWT login
│   │   ├── batches.py          # Farm harvest batch management
│   │   ├── crop_profiles.py    # Reference data for crops
│   │   ├── disputes.py         # Cold-chain liability claims
│   │   ├── health.py           # Health checks
│   │   ├── intake.py           # Buyer destination check-in
│   │   ├── listings.py         # Marketplace listings
│   │   ├── orders.py           # Order booking & inventory reservation
│   │   ├── passport.py         # Public Bio-Clock passport QR data
│   │   ├── pools.py            # Transport pooling & vehicle telemetry
│   │   └── users.py            # User profile management
│   ├── services/               # DSP, pooling, decay, weather algorithms
│   ├── main.py                 # FastAPI application entry point
│   ├── schemas.py              # Pydantic v2 contract DTOs
│   └── seed.py                 # Demo bootstrap seed data
├── frontend/                   # Next.js 15 App Router Frontend
│   ├── app/                    # Next.js pages & dashboard views
│   ├── components/             # Reusable UI components
│   ├── lib/                    # API client, AudioWorklet recorder, mock store
│   └── next.config.mjs         # API proxy & rewrite configurations
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel multi-service monorepo configuration
└── README.md                   # Project documentation
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 20.9+** and **npm**

### 1. Backend Setup (FastAPI)
```bash
# Clone the repository
git clone https://github.com/saahil-2008/snack-overflow.git
cd snack-overflow

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend development server (starts on http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```
Swagger UI will be available at: **`http://localhost:8000/docs`**

---

### 2. Frontend Setup (Next.js)
```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server (starts on http://localhost:3000)
npm run dev
```
Open **`http://localhost:3000`** in your browser.

> **Note:** The frontend automatically proxies all `/api/v1/*` calls to `http://localhost:8000` via Next.js rewrites, so there are zero CORS configuration issues locally.

---

## 👥 Seeded Demo Accounts

On initial startup with `SEED_DEMO=true`, the database is automatically pre-seeded with ready-to-test accounts:

| Role | Name | Phone | Password | Organization / Region |
| :--- | :--- | :--- | :--- | :--- |
| **FARMER** | Ramesh Pawar | `+919800000001` | `Demo@12345` | Pimpalgaon Tomato FPO (Nashik) |
| **LOGISTICS** | Sunita Logistics | `+919800000002` | `Demo@12345` | Sahyadri Reefer Lines |
| **BUYER** | Arjun Mehta | `+919800000003` | `Demo@12345` | Nashik Road Dark Store 4 |
| **ADMIN / AGRONOMIST** | Dr. Priya Rao | `+919800000004` | `Demo@12345` | ICAR Post-Harvest Directorate |

---

## 🌐 Deployment

### Option A: Vercel Multi-Service Monorepo (Included `vercel.json`)
The repository is pre-configured with Vercel's multi-service architecture:
- **`frontend` service:** Public Next.js web application handling all inbound traffic.
- **`app` service:** Internal FastAPI service bound to Next.js via internal `APP_URL` bindings.

Simply import the GitHub repository in [Vercel](https://vercel.com) and deploy.

### Option B: Standalone Web Service (Render / Railway)
If deploying backend on Render and frontend on Vercel:
- **Render Build Command:** `pip install -r requirements.txt`
- **Render Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set `NEXT_PUBLIC_API_BASE_URL` on the frontend to your Render URL.

---

## 📜 License & Acknowledgements
Built with ❤️ during the hackathon for smallholder farmers across India. Open-Meteo weather data provided under CC BY 4.0.
