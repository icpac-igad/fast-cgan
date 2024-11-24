from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from fastcgan.models.shared import HealthCheck
from fastcgan.tools.config import settings

router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def app_health_check(request: Request):
    return HealthCheck(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt() -> str:
    return "User-agent: *\nAllow: /"


@router.get("/favicon.ico", status_code=404, response_class=PlainTextResponse)
async def favicon_ico() -> str:
    return "page not found"
