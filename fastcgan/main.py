# from fastcgan.routes import router
from fastapi.middleware.cors import CORSMiddleware

from fastcgan.routes.forecast import router as forecast_router
from fastcgan.routes.healthz import router as healthz_router
from fastcgan.routes.settings import router as settings_router
from fastcgan.tools import enums
from fastcgan.tools.config import get_allowed_cor_origins, settings
from fastcgan.tools.setup import create_application

app = create_application(settings=settings, root_path=settings.APP_SUBPATH)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_cor_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(healthz_router, tags=[enums.RouterTag.general], prefix="")
app.include_router(settings_router, tags=[enums.RouterTag.settings], prefix="/settings")
app.include_router(forecast_router, tags=[enums.RouterTag.forecast], prefix="/forecast")
