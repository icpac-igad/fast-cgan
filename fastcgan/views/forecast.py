from datetime import datetime
from pathlib import Path

import xarray as xr
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES
from show_forecasts.show_cGAN import (
    load_GAN_forecast,
    plot_GAN_ensemble,
    plot_GAN_forecast,
    plot_GAN_local_histograms,
    plot_GAN_threshold_chance,
    plot_location_marker,
)
from show_forecasts.show_IFS_open_data import load_forecast as load_open_ifs_data
from show_forecasts.show_IFS_open_data import plot_forecast as plot_open_ifs_forecast
from show_forecasts.show_IFS_open_data import (
    plot_forecast_ensemble as plot_ifs_forecast_ensemble,
)

from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    PrecipitationUnit,
    ValidStartTime,
)
from fastcgan.tools.utils import get_data_store_path, get_forecast_data_dates
from fastcgan.views.tools import (
    get_forecast_maps_path,
    get_local_histogram_chart,
    get_location_marker_map,
)


async def open_ifs_forecast(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
) -> list[list[Path], xr.Dataset | None]:
    source = "open-ifs"
    if data_date is None:
        data_dates = get_forecast_data_dates(
            mask_region=mask_area,
            source=source,
        )
        data_date = data_dates[0]
    data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
    )
    maps_exist = [file_path.exists() for file_path in maps_path]
    if not all(maps_exist if len(maps_path) == 1 else maps_exist[:-1]):
        data_store = get_data_store_path(source=source)
        data = load_open_ifs_data(
            key=vis_param.name,
            forecast_init_date=data_date_obj,
            data_dir=str(data_store),
            mask_region=mask_area,
            status_updates=False,
            cgan_ui_fs=True,
        )
        plot_open_ifs_forecast(
            data=data,
            style=color_style,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path


async def open_ifs_forecast_ensemble(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
) -> list[Path]:
    source = "open-ifs"
    if data_date is None:
        data_dates = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=source,
        )
        data_date = data_dates[0]
    data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        ensemble=True,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=source)
        data = load_open_ifs_data(
            key=vis_param.name,
            forecast_init_date=data_date_obj,
            data_dir=str(data_store),
            mask_region=mask_area,
            status_updates=False,
            cgan_ui_fs=True,
        )
        plot_ifs_forecast_ensemble(
            data=data,
            style=color_style,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path


async def cgan_forecast(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    acc_time: AccumulationTime | None = AccumulationTime.hour6,
    start_time: ValidStartTime | None = ValidStartTime.six,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
) -> list[list[Path], xr.Dataset | None]:
    source = "cgan"
    if data_date is None:
        data_dates = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=source,
        )
        data_date = data_dates[0]
    data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        start_time=start_time,
        acc_time=acc_time,
    )
    maps_exist = [file_path.exists() for file_path in maps_path]
    if not all(maps_exist if len(maps_path) == 1 else maps_exist[:-1]):
        data_store = get_data_store_path(source=source)
        data = load_GAN_forecast(
            forecast_init_date=data_date_obj,
            data_dir=str(data_store),
            mask_region=mask_area,
            cgan_ui_fs=True,
        )
        plot_GAN_forecast(
            data=data,
            style=color_style,
            plot_units=plot_units.value,
            accumulation_time=acc_time.value,
            valid_time_start_hour=start_time.value,
            region=mask_area,
            show_plot=False,
            file_name=str(maps_path[-1]),
        )
    return maps_path if len(maps_path) == 1 else maps_path[:-1]


async def cgan_forecast_ensemble(
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    start_time: ValidStartTime | None = ValidStartTime.six,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
    max_ens_plots: int | None = 50,
) -> list[Path]:
    source = "cgan"
    start_time = start_time if start_time != ValidStartTime.combine else ValidStartTime.six
    if data_date is None:
        data_dates = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=source,
        )
        data_date = data_dates[0]
    data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        start_time=start_time,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        ensemble=True,
        max_ens_plots=max_ens_plots,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=source)
        data = load_GAN_forecast(
            forecast_init_date=data_date_obj,
            data_dir=str(data_store),
            mask_region=mask_area,
            cgan_ui_fs=True,
        )
        plot_GAN_ensemble(
            data=data,
            valid_time_start_hour=start_time.value,
            style=color_style,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
            max_num_plots=max_ens_plots,
        )
    return maps_path


async def cgan_threshold_chance(
    threshold: float | None = 5,
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    start_time: ValidStartTime | None = ValidStartTime.six,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
    show_percentages: bool | None = None,
) -> list[Path]:
    source = "cgan"
    if data_date is None:
        data_dates = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=source,
        )
        data_date = data_dates[0]
    data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=source,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        threshold=threshold,
        show_percentages=show_percentages,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=source)
        data = load_GAN_forecast(
            forecast_init_date=data_date_obj,
            data_dir=str(data_store),
            mask_region=mask_area,
            cgan_ui_fs=True,
        )
        plot_GAN_threshold_chance(
            data=data,
            style=color_style,
            threshold=threshold,
            plot_units=plot_units.value,
            valid_time_start_hour=start_time.value,
            show_percentages=show_percentages,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path


async def cgan_local_histogram(
    data_date: str | None = None,
    location: str | None = "LatLng",
    country: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    num_bins: int | None = 10,
    probability: float | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
) -> list[Path]:
    map_images = []
    marker_map = await get_location_marker_map(
        location=location, latitude=latitude, longitude=longitude, region=country
    )
    if not marker_map.exists():
        plot_location_marker(
            location_name=location,
            region=country,
            latitude=latitude,
            longitude=longitude,
            file_name=str(marker_map),
            show_plot=False,
        )

    if marker_map.exists():
        map_images.append(marker_map)
        source = "cgan"
        if data_date is None:
            data_dates = get_forecast_data_dates(
                mask_region=COUNTRY_NAMES[0],
                source=source,
            )
            data_date = data_dates[0]
        data_date_obj = datetime.strptime(data_date, "%b %d, %Y")
        hist_path = await get_local_histogram_chart(
            data_date=data_date_obj,
            location=location,
            country=country,
            latitude=latitude,
            longitude=longitude,
            plot_units=plot_units,
            num_bins=num_bins,
            probability=probability,
        )

        if not hist_path.exists():
            data_store = get_data_store_path(source=source)
            data = load_GAN_forecast(
                forecast_init_date=data_date_obj,
                data_dir=str(data_store),
                mask_region=mask_area,
                cgan_ui_fs=True,
            )
            plot_GAN_local_histograms(
                data=data,
                location_name=location,
                country=country,
                latitude=latitude,
                longitude=longitude,
                plot_units=plot_units.value,
                probability=probability,
                file_name=str(hist_path),
                show_plot=False,
            )

        if hist_path.exists():
            map_images.append(hist_path)

    return map_images
