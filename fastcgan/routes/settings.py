from typing import Literal

from fastapi import APIRouter
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.jobs.utils import get_forecast_data_dates
from fastcgan.models import settings
from fastcgan.tools.constants import GAN_MODELS

router = APIRouter()


@router.get("/gan-forecast-models", response_model=list[settings.ForecastModel])
async def get_gan_forecast_models() -> list[settings.ForecastModel]:
    return [settings.ForecastModel(**model) for model in GAN_MODELS]


@router.get("/data-dates", response_model=list[settings.ForecastDate])
async def get_forecast_dates(
    model: Literal["jurre-brishti", "mvua-kubwa", "open-ifs"] | None = "jurre-brishti",
) -> list[settings.ForecastDate]:
    data_dates = get_forecast_data_dates(
        source=model if model == "open-ifs" else f"{model}-ens",
        mask_region=(None if model in ["jurre-brishti", "mvua-kubwa"] else COUNTRY_NAMES[0]),
    )
    return [settings.ForecastDate(date=data_date) for data_date in data_dates]


@router.get("/mask-areas", response_model=list[settings.MaskArea])
async def get_mask_areas() -> list[settings.MaskArea]:
    return [settings.MaskArea(name=mask_area) for mask_area in COUNTRY_NAMES]


@router.get("/color-styles", response_model=list[settings.VisualizationColorStyle])
async def get_color_styles() -> list[settings.VisualizationColorStyle]:
    return [
        settings.VisualizationColorStyle(name=color_style)
        for color_style in COLOR_SCHEMES
        if color_style not in ["ICPAC_heavy", "EMI_heavy"]
    ]
