from fastapi import APIRouter, Query

from fastcgan.models import settings
from fastcgan.models.routes import (
    GanEnsembleHistogramParams,
    GanEnsembleParams,
    GanForecastParams,
    GanThresholdChanceParams,
    OpenIfsParams,
)
from fastcgan.tools.config import get_cached_file_url
from fastcgan.views.forecast import (
    cgan_forecast,
    cgan_forecast_ensemble,
    cgan_local_histogram,
    cgan_threshold_chance,
    open_ifs_forecast,
    open_ifs_forecast_ensemble,
)

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


@router.get(
    "/cgan-histogram",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_cgan_histogram_plot(
    params: GanEnsembleHistogramParams = Query(),
) -> list[settings.ForecastMap]:
    imgs_paths = []
    if params.latitude is not None and params.longitude is not None:
        imgs_paths = await cgan_local_histogram(**params.model_dump(exclude_unset=True))

    elif params.location is not None and params.location != "LatLng":
        # location, country = params.location.split("-")
        imgs_paths = await cgan_local_histogram(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]
