"""FarmPool 360 API entry point. Run: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.core.config import CORS_EXTRA_ORIGINS, FRONTEND_BASE_URL, SEED_DEMO
from app.core.errors import install_error_handling
from app.db.session import SessionLocal, create_tables
from app.routers import (
    advisories,
    assay,
    auth,
    batches,
    crop_profiles,
    disputes,
    health,
    intake,
    listings,
    orders,
    passport,
    pools,
    users,
)
from app.seed import seed_demo_data

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("farmpool")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    if SEED_DEMO:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title="FarmPool 360 × ChronoCrop",
    version="1.1.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

origins = list(dict.fromkeys([
    FRONTEND_BASE_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    *filter(None, (o.strip() for o in CORS_EXTRA_ORIGINS.split(","))),
]))
install_error_handling(app, origins)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(crop_profiles.router)
app.include_router(advisories.router)
app.include_router(batches.router)
app.include_router(assay.router)
app.include_router(pools.router)
app.include_router(listings.router)
app.include_router(orders.router)
app.include_router(intake.router)
app.include_router(disputes.router)
app.include_router(passport.router)
