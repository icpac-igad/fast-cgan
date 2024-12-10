from fastapi import APIRouter, Query

from fastcgan.models import settings
from fastcgan.models.routes import (
    GanEnsembleHistogramParams,
    GanEnsembleParams,
    GanForecastParams,
    GanThresholdChanceParams,
    OpenIfsParams,
)
from fastcgan.tools.config import get_cached_file_url, get_major_towns_data
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

    else:
        locations = get_major_towns_data()
        if params.location is None:
            location = locations[0]
        else:
            town_name, gid_3 = params.location.split("-")
            town = [loc for loc in locations if loc["TOWN_NAME"] == town_name and loc["gid_3"] == gid_3]
            location = locations[0] if not len(town) else town[0]
        params.latitude = location["lat"]
        params.longitude = location["lon"]
        imgs_paths = await cgan_local_histogram(**params.model_dump(exclude_unset=True))
    return [(settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path))) for img_path in imgs_paths]
