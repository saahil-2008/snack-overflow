# app/routers/health.py
from fastapi import APIRouter

from app.core.config import CONTRACT_VERSION
from app.schemas import ApiSuccess, HealthStatus

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", status_code=200, response_model=ApiSuccess[HealthStatus])
async def health():
    return ApiSuccess(data=HealthStatus(version=CONTRACT_VERSION))
