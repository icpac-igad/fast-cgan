from datetime import datetime
from pathlib import Path

import xarray as xr
from loguru import logger
from show_forecasts.constants import COUNTRY_NAMES
from show_forecasts.show_cGAN import (
    load_GAN_forecast,
    plot_GAN_ensemble,
    plot_GAN_forecast,
    plot_GAN_threshold_chance,
)

from fastcgan.jobs.stubs import cgan_model_literal
from fastcgan.jobs.utils import get_data_store_path, get_forecast_data_dates
from fastcgan.tools.constants import GAN_MODELS
from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    InitializationTime,
    MapColorScheme,
    PrecipitationUnit,
    ValidityTime,
)
from fastcgan.views.tools import get_forecast_maps_path


async def cgan_forecast(
    model: cgan_model_literal | None = GAN_MODELS[0]["name"],
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day,
    acc_time: AccumulationTime | None = AccumulationTime.half_day,
    init_time: InitializationTime | None = InitializationTime.midnight,
    valid_time: ValidityTime | None = None,
    forecast_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: MapColorScheme | None = MapColorScheme.icpac,
) -> list[list[Path], xr.Dataset | None]:
    if forecast_date is None:
        forecast_date = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=model,
        )[0]
    if valid_time is None:
        valid_time = ValidityTime.plus30h if model == "jurre-brishti" else ValidityTime.plus6h
    data_date_obj = datetime.strptime(forecast_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=model,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        init_time=init_time,
        acc_time=acc_time,
        valid_time=valid_time,
    )
    maps_exist = [file_path.exists() for file_path in maps_path]
    if not all(maps_exist if len(maps_path) == 1 else maps_exist[:-1]):
        data_store = get_data_store_path(source=model)
        try:
            data = load_GAN_forecast(
                model=f"{model}-ens",
                init_date=data_date_obj,
                init_time=init_time.value.replace("h", ""),
                data_dir=str(data_store).replace(f"/{model}-ens", ""),
                mask_region=mask_area,
                cgan_ui_fs=True,
            )
        except Exception as err:
            logger.error(f"failed to plot cGAN forecast with error: {err}")
            return []
        plot_GAN_forecast(
            data=data,
            model=f"{model}-ens",
            style=color_style.value,
            plot_units=plot_units.value,
            accumulation_time=acc_time.value,
            valid_time_start_hour=valid_time.value,
            region=mask_area,
            show_plot=False,
            file_name=str(maps_path[-1]),
        )
    return maps_path if len(maps_path) == 1 else maps_path[:-1]


async def cgan_forecast_ensemble(
    model: cgan_model_literal | None = GAN_MODELS[0]["name"],
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day,
    init_time: InitializationTime | None = InitializationTime.midnight,
    valid_time: ValidityTime | None = None,
    forecast_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: MapColorScheme | None = MapColorScheme.icpac,
    max_ens_plots: int | None = 50,
    **kwagrs,
) -> list[Path]:
    if forecast_date is None:
        forecast_date = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=model,
        )[0]
    if valid_time is None:
        valid_time = ValidityTime.plus30h if model == "jurre-brishti" else ValidityTime.plus6h
    data_date_obj = datetime.strptime(forecast_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=model,
        vis_param=vis_param,
        plot_units=plot_units,
        init_time=init_time,
        valid_time=valid_time,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        ensemble=True,
        max_ensemble_plots=max_ens_plots,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=model)
        try:
            data = load_GAN_forecast(
                model=f"{model}-ens",
                init_date=data_date_obj,
                init_time=init_time.value.replace("h", ""),
                data_dir=str(data_store).replace(f"/{model}-ens", ""),
                mask_region=mask_area,
                cgan_ui_fs=True,
            )
        except Exception as err:
            logger.error(f"failed to plot cGAN ensemble forecast with error: {err}")
            return []
        plot_GAN_ensemble(
            data=data,
            model=f"{model}-ens",
            valid_time_start_hour=valid_time.value,
            style=color_style.value,
            plot_units=plot_units.value,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
            max_num_plots=max_ens_plots,
        )
    return maps_path


async def cgan_threshold_chance(
    model: cgan_model_literal | None = GAN_MODELS[0]["name"],
    threshold: float | None = 5,
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day,
    init_time: InitializationTime | None = InitializationTime.midnight,
    valid_time: ValidityTime | None = None,
    forecast_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: MapColorScheme | None = MapColorScheme.icpac,
    show_percentages: bool | None = None,
    **kwargs,
) -> list[Path]:
    if forecast_date is None:
        forecast_date = get_forecast_data_dates(
            mask_region=COUNTRY_NAMES[0],
            source=model,
        )[0]
    if valid_time is None:
        valid_time = ValidityTime.plus30h if model == "jurre-brishti" else ValidityTime.plus6h
    data_date_obj = datetime.strptime(forecast_date, "%b %d, %Y")
    maps_path = await get_forecast_maps_path(
        source=model,
        vis_param=vis_param,
        plot_units=plot_units,
        data_date=data_date_obj,
        mask_area=mask_area,
        color_style=color_style,
        threshold=threshold,
        show_percentages=show_percentages,
        init_time=init_time,
        valid_time=valid_time,
    )
    if not maps_path[0].exists():
        data_store = get_data_store_path(source=model)
        try:
            data = load_GAN_forecast(
                model=f"{model}-ens",
                init_date=data_date_obj,
                init_time=init_time.value.replace("h", ""),
                data_dir=str(data_store).replace(f"/{model}-ens", ""),
                mask_region=mask_area,
                cgan_ui_fs=True,
            )
        except Exception as err:
            logger.error(f"failed to plot cGAN threshold exceedence forecast with error: {err}")
            return []
        plot_GAN_threshold_chance(
            data=data,
            model=f"{model}-ens",
            style=color_style.value,
            threshold=threshold,
            plot_units=plot_units.value,
            valid_time_start_hour=valid_time.value,
            show_percentages=show_percentages,
            region=mask_area,
            file_name=str(maps_path[-1]),
            show_plot=False,
        )
    return maps_path
