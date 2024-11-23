from fastapi import APIRouter, Request

from fastcgan.config import settings
from fastcgan.models.shared import HealthCheck
from fastcgan.routes import limiter

router = APIRouter()


@router.get("/", response_model=HealthCheck)
@limiter.limit("5/minute")
async def app_health_check(request: Request):
    return HealthCheck(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
    )
