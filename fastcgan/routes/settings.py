from fastapi import APIRouter
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.jobs.stubs import cgan_model_literal
from fastcgan.jobs.utils import get_forecast_data_dates, get_locations_data_for_region
from fastcgan.models import settings
from fastcgan.tools.constants import GAN_MODELS

router = APIRouter()


@router.get("/gan-forecast-models", response_model=list[settings.ForecastModel])
async def get_gan_forecast_models() -> list[settings.ForecastModel]:
    return [settings.ForecastModel(**model) for model in GAN_MODELS]


@router.get("/data-dates", response_model=list[settings.ForecastDate])
async def get_forecast_dates(
    forecast: cgan_model_literal | None = GAN_MODELS[0]["name"],
) -> list[settings.ForecastDate]:
    data_dates = get_forecast_data_dates(
        source=f"{forecast}-count",
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


@router.get("/locations", response_model=list[settings.MaskArea])
async def get_predefined_locations(
    q: str | None = None,
) -> list[settings.MaskArea]:
    mask_area = (
        COUNTRY_NAMES[0] if q is None or q == "" else [area for area in COUNTRY_NAMES if q.lower() in area.lower()]
    )
    if isinstance(mask_area, list):
        mask_area = COUNTRY_NAMES[0] if not len(mask_area) else mask_area[0]
    locations = get_locations_data_for_region(mask_area)
    return [settings.MaskArea(name=f"{location['name']}-{location['country']}") for location in locations]
