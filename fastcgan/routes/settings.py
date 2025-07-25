from typing import Literal

from fastapi import APIRouter
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.jobs.utils import (
    get_cgan_forecast_dates,
    get_forecast_data_dates,
    get_forecast_initialization_times,
)
from fastcgan.models import settings
from fastcgan.tools.constants import GAN_MODELS

router = APIRouter()


@router.get("/gan-forecast-models", response_model=list[settings.ForecastModel])
async def get_gan_forecast_models(
    no_ensemble: int | None = 50,
) -> list[settings.ForecastModel]:
    model_pref = "count" if no_ensemble == 1000 else "ens"
    return [
        settings.ForecastModel(
            name=f"{model['name']}-{model_pref}",
            label=model["label"],
            value=model["value"],
        )
        for model in GAN_MODELS
    ]


@router.get("/data-dates", response_model=list[settings.ForecastDate])
async def get_forecast_dates(
    model: (
        Literal[
            "jurre-brishti-ens",
            "mvua-kubwa-ens",
            "jurre-brishti-count",
            "mvua-kubwa-count",
            "open-ifs",
        ]
        | None
    ) = "jurre-brishti-ens",
) -> list[settings.ForecastDate]:
    model = model if model is not None else "jurre-brishti-ens"
    data_dates = get_forecast_data_dates(
        source=model,
        mask_region=None if "count" in model else COUNTRY_NAMES[0],
    )
    return [settings.ForecastDate(date=data_date) for data_date in data_dates]


@router.get("/cgan-dates", response_model=list[settings.GanOutputDate])
async def get_cgan_forecasts_dates(
    model: (
        Literal[
            "jurre-brishti-ens",
            "mvua-kubwa-ens",
            "jurre-brishti-count",
            "mvua-kubwa-count",
        ]
        | None
    ) = "jurre-brishti-ens",
) -> list[settings.GanOutputDate]:
    cgan_dates = get_cgan_forecast_dates(source=model if model is not None else "jurre-brishti-ens")
    return cgan_dates


@router.get("/forecast-init-time", response_model=list[settings.ForecastInitTime])
async def get_forecast_init_time(
    forecast_date: str | None = None,
    model_name: (Literal["jurre-brishti-ens", "jurre-brishti-count"] | None) = "jurre-brishti-ens",
) -> list[settings.ForecastInitTime]:
    fcst_times = get_forecast_initialization_times(data_date=forecast_date, model=model_name)
    return [settings.ForecastInitTime(hour=init_time) for init_time in fcst_times]


@router.get("/mask-areas", response_model=list[settings.MaskArea])
async def get_mask_areas() -> list[settings.MaskArea]:
    return [settings.MaskArea(name=mask_area) for mask_area in COUNTRY_NAMES]


@router.get("/color-styles", response_model=list[settings.VisualizationColorStyle])
async def get_color_styles() -> list[settings.VisualizationColorStyle]:
    return [settings.VisualizationColorStyle(name=color_style) for color_style in COLOR_SCHEMES if color_style not in ["ICPAC_heavy", "EMI_heavy"]]
