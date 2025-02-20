from fastapi import APIRouter, Query

from fastcgan.models import settings
from fastcgan.models.routes import (
    GanEnsembleParams,
    GanForecastParams,
    GanThresholdChanceParams,
)
from fastcgan.tools.config import get_cached_file_url
from fastcgan.views.forecast import (
    cgan_forecast,
    cgan_forecast_ensemble,
    cgan_threshold_chance,
)

router = APIRouter()


@router.get(
    "/cgan-forecast",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_cgan_forecast(
    params: GanForecastParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = await cgan_forecast(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]


@router.get(
    "/cgan-ensemble",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_cgan_forecast_ensemble_plot(
    params: GanEnsembleParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = await cgan_forecast_ensemble(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]


@router.get(
    "/cgan-threshold-chance",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_cgan_theshold_chance_plot(
    params: GanThresholdChanceParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = await cgan_threshold_chance(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]
