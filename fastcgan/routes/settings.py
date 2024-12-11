from typing import Literal

from fastapi import APIRouter
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.models import settings
from fastcgan.tools.utils import get_forecast_data_dates, get_locations_data_for_region

router = APIRouter()


@router.get("/data-dates", response_model=list[settings.ForecastDate])
async def get_forecast_dates(
    forecast: Literal["cgan-forecast", "open-ifs"] | None = "cgan-forecast",
) -> list[settings.ForecastDate]:
    data_dates = get_forecast_data_dates(
        mask_region=COUNTRY_NAMES[0],
        source=forecast,
    )
    return [settings.ForecastDate(date=data_date) for data_date in data_dates]


@router.get("/mask-areas", response_model=list[settings.MaskArea])
async def get_mask_areas() -> list[settings.MaskArea]:
    return [settings.MaskArea(name=mask_area) for mask_area in COUNTRY_NAMES]


@router.get("/color-styles", response_model=list[settings.VisualizationColorStyle])
async def get_color_styles() -> list[settings.VisualizationColorStyle]:
    return [settings.VisualizationColorStyle(name=color_style) for color_style in COLOR_SCHEMES]


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
