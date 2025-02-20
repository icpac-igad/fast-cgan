from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, PlainTextResponse

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


if settings.REDOC_URL is not None:

    @router.get("/redoc", include_in_schema=False)
    async def get_redoc_documentation() -> HTMLResponse:
        return get_redoc_html(openapi_url=f"{settings.APP_SUBPATH}/openapi.json", title="Redoc Playground")


if settings.REDOC_URL is not None:

    @router.get("/docs", include_in_schema=False)
    async def get_swagger_documentation() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url=f"{settings.APP_SUBPATH}/openapi.json", title="Swagger Docs")
