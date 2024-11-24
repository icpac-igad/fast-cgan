# from fastcgan.routes import router
from fastapi import APIRouter

from fastcgan.routes.forecast import router as forecast_router
from fastcgan.routes.healthz import router as healthz_router
from fastcgan.routes.settings import router as settings_router
from fastcgan.tools import enums
from fastcgan.tools.config import settings
from fastcgan.tools.setup import create_application

app = create_application(router=APIRouter(prefix="/api"), settings=settings)

app.include_router(healthz_router, tags=[enums.RouterTag.general], prefix="")
app.include_router(settings_router, tags=[enums.RouterTag.settings], prefix="/settings")
app.include_router(forecast_router, tags=[enums.RouterTag.forecast], prefix="/forecast")
