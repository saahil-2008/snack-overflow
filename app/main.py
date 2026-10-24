"""FarmPool API entry point. Run: python -m uvicorn app.main:app --reload."""
from contextlib import asynccontextmanager
from importlib import import_module
from fastapi import FastAPI
from app.core.config import CORS_EXTRA_ORIGINS, FRONTEND_BASE_URL, SEED_DEMO
from app.core.errors import install_error_handling
from app.db.session import create_tables, SessionLocal
from app.seed import seed_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    if SEED_DEMO:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield

app = FastAPI(title="FarmPool 360 × ChronoCrop", version="1.1.0", redirect_slashes=False, lifespan=lifespan)
origins = list(dict.fromkeys([FRONTEND_BASE_URL, "http://localhost:3000", "http://127.0.0.1:3000", *filter(None, CORS_EXTRA_ORIGINS.split(","))]))
install_error_handling(app, origins)
for name in ("health", "auth", "users", "crop_profiles", "advisories", "batches", "passport", "assay", "pools", "listings", "orders", "intake", "disputes"):
    app.include_router(import_module(f"app.routers.{name}").router)
