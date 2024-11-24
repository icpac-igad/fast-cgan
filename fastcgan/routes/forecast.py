from fastapi import APIRouter
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.models import settings
from fastcgan.tools.config import get_cached_file_url
from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    PrecipitationUnit,
    ValidStartTime,
)
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
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
    show_ensemble: bool | None = False,
) -> list[settings.ForecastMap]:
    imgs_paths, data = await open_ifs_forecast(
        vis_param=vis_param,
        data_date=data_date,
        mask_area=mask_area,
        color_style=color_style,
        plot_units=plot_units,
    )
    if show_ensemble:
        imgs_paths.extend(
            await open_ifs_forecast_ensemble(
                data=data,
                vis_param=vis_param,
                data_date=data_date,
                mask_area=mask_area,
                color_style=color_style,
                plot_units=plot_units,
            )
        )
    return [
        (settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path)))
        for img_path in imgs_paths
    ]


@router.get(
    "/cgan",
    response_model=list[settings.ForecastMap],
    response_model_exclude_none=True,
)
async def get_cgan_forecast(
    show_cgan: bool | None = False,
    vis_param: IfsDataParameter | None = IfsDataParameter.tp,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6,
    acc_time: AccumulationTime | None = AccumulationTime.hour6,
    start_time: ValidStartTime | None = ValidStartTime.combine,
    data_date: str | None = None,
    mask_area: str | None = COUNTRY_NAMES[0],
    color_style: str | None = COLOR_SCHEMES[0],
    show_ensemble: bool | None = False,
    max_ensemble_plots: int | None = 10,
    thres_chance: bool | None = False,
    threshold: float | None = 5,
    show_percentages: bool | None = False,
    show_hist: bool | None = False,
    location: str | None = "LatLng",
    latitude: float | None = None,
    longitude: float | None = None,
    num_bins: int | None = 10,
    probability: float | None = None,
) -> list[settings.ForecastMap]:
    imgs_paths, data = await cgan_forecast(
        vis_param=vis_param,
        acc_time=acc_time,
        start_time=start_time,
        data_date=data_date,
        mask_area=mask_area,
        color_style=color_style,
        plot_units=plot_units,
    )
    if show_ensemble:
        imgs_paths.extend(
            await cgan_forecast_ensemble(
                data=data,
                vis_param=vis_param,
                start_time=start_time,
                data_date=data_date,
                mask_area=mask_area,
                color_style=color_style,
                plot_units=plot_units,
                max_ensemble_plots=max_ensemble_plots,
            )
        )
    if thres_chance:
        imgs_paths.extend(
            await cgan_threshold_chance(
                vis_param=vis_param,
                start_time=start_time,
                data_date=data_date,
                mask_area=mask_area,
                color_style=color_style,
                plot_units=plot_units,
                show_percentages=show_percentages,
                threshold=threshold,
            )
        )
    if show_hist:
        if latitude is not None and longitude is not None:
            imgs_paths.extend(
                await cgan_local_histogram(
                    data_date=data_date,
                    plot_units=plot_units,
                    mask_area=mask_area,
                    latitude=latitude,
                    longitude=longitude,
                    probability=probability,
                    num_bins=num_bins,
                )
            )

        elif location is not None and location != "LatLng":
            location, country = location.split("-")
            imgs_paths.extend(
                await cgan_local_histogram(
                    data_date=data_date,
                    plot_units=plot_units,
                    mask_area=mask_area,
                    country=country,
                    location=location,
                    probability=probability,
                    num_bins=num_bins,
                )
            )
    return [
        (settings.ForecastMap(image_url=get_cached_file_url(file_path=img_path)))
        for img_path in imgs_paths
    ]
