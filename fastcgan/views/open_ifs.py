from datetime import datetime
from pathlib import Path

import xarray as xr
from show_forecasts.constants import COUNTRY_NAMES
from show_forecasts.show_IFS_open_data import load_forecast as load_open_ifs_data
from show_forecasts.show_IFS_open_data import plot_forecast as plot_open_ifs_forecast
from show_forecasts.show_IFS_open_data import (
    plot_forecast_ensemble as plot_ifs_forecast_ensemble,
)

from fastcgan.jobs.utils import get_data_store_path, get_forecast_data_dates
from fastcgan.tools.enums import IfsDataParameter, MapColorScheme, PrecipitationUnit
from fastcgan.views.tools import get_forecast_maps_path


async def open_ifs_forecast(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day,
    forecast_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: MapColorScheme | None = MapColorScheme.icpac,
) -> list[list[Path], xr.Dataset | None]:
    source = "open-ifs"
    if forecast_date is None:
        forecast_dates = get_forecast_data_dates(
            mask_region=mask_area,
            source=source,
        )
        if not len(forecast_dates):
            return []
        forecast_date = forecast_dates[0]
    data_date_obj = datetime.strptime(forecast_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=MapColorScheme.icpac if color_style is None else color_style.value,
    )
    maps_exist = [file_path.exists() for file_path in maps_path]
    if not all(maps_exist if len(maps_path) == 1 else maps_exist[:-1]):
        data_store = get_data_store_path(source=source)
        try:
            data = load_open_ifs_data(
                key=vis_param.name,
                forecast_init_date=data_date_obj,
                data_dir=str(data_store),
                mask_region=mask_area,
                status_updates=False,
                cgan_ui_fs=True,
            )
        except Exception:
            return []
        plot_open_ifs_forecast(
            data=data,
            style=MapColorScheme.icpac if color_style is None else color_style.value,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path


async def open_ifs_forecast_ensemble(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day,
    forecast_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: MapColorScheme | None = MapColorScheme.icpac,
) -> list[Path]:
    vis_param = IfsDataParameter.tp
    source = "open-ifs"
    if forecast_date is None:
        forecast_dates = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=source,
        )
        if not len(forecast_dates):
            return []
        forecast_date = forecast_dates[0]
    data_date_obj = datetime.strptime(forecast_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=MapColorScheme.icpac if color_style is None else color_style.value,
        ensemble=True,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=source)
        try:
            data = load_open_ifs_data(
                key=vis_param.name,
                forecast_init_date=data_date_obj,
                data_dir=str(data_store),
                mask_region=mask_area,
                status_updates=False,
                cgan_ui_fs=True,
            )
        except Exception:
            return []
        plot_ifs_forecast_ensemble(
            data=data,
            style=MapColorScheme.icpac if color_style is None else color_style.value,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path
