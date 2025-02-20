from fastapi import APIRouter, Query

from fastcgan.models import settings
from fastcgan.models.routes import (
    OpenIfsParams,
)
from fastcgan.tools.config import get_cached_file_url
from fastcgan.views.open_ifs import open_ifs_forecast, open_ifs_forecast_ensemble

router = APIRouter()


@router.get(
    "/open-ifs",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_open_ifs_forecast(
    params: OpenIfsParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = await open_ifs_forecast(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]


@router.get(
    "/open-ifs-ensemble",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_open_ifs_forecast_ensemble_plots(
    params: OpenIfsParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = await open_ifs_forecast_ensemble(
        **params.model_dump(exclude_unset=True),
    )
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]
