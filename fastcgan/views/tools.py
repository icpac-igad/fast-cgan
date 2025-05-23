from datetime import datetime
from pathlib import Path

from fastcgan.tools.config import get_cached_file_base_path
from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    InitializationTime,
    MapColorScheme,
    PrecipitationUnit,
    ValidityTime,
)


async def get_forecast_maps_path(
    source: str,
    vis_param: IfsDataParameter,
    plot_units: PrecipitationUnit,
    data_date: datetime,
    mask_area: str,
    color_style: MapColorScheme,
    valid_time: ValidityTime | None = None,
    init_time: InitializationTime | None = None,
    acc_time: AccumulationTime | None = None,
    threshold: float | None = None,
    show_percentages: bool | None = False,
    ensemble: bool | None = False,
    max_ensemble_plots: int | None = 50,
    extension: str | None = "png",
) -> list[Path]:
    data_date_str = data_date.strftime("%Y_%m_%d")
    fname_str = (
        f"{source.replace('-','_')}-{mask_area.lower().replace(' ','_')}-"
        + f"{vis_param.value.lower().replace(' ','_')}-{plot_units.value.replace('/','_')}"
        + f"-{color_style.value.lower()}-{data_date_str}"
    )
    if init_time is not None:
        fname_str += f"-init_{init_time.value}"
    if valid_time is not None:
        fname_str += f"-valid_{valid_time.value}"
    if acc_time is not None:
        fname_str += f"-acc_{acc_time.value}"
    if ensemble:
        fname_str += f"-{max_ensemble_plots}_ens_plots"
    if show_percentages:
        fname_str += "-percentage"
    if threshold is not None:
        fname_str += f"-chance_threshold_{threshold:.2f}".replace(".", "_")
    return [get_cached_file_base_path(source=source) / f"{fname_str}.{extension}"]


async def get_local_histogram_chart(
    data_date: datetime,
    location: str | None = "LatLng",
    country: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour,
    num_bins: int | None = 10,
    probability: float | None = None,
    extension: str | None = "png",
) -> Path:
    data_date_str = data_date.strftime("%Y_%m_%d")
    fname_str = f"pixel-histogram-{location.lower().replace(' ','_')}-{data_date_str}"
    if country is not None:
        fname_str += f"-{country.lower().replace(' ', '_')}"
    if latitude is not None and longitude is not None:
        fname_str += f"-lat_{latitude:.2f}_lng_{longitude:.2f}".replace(".", "_")
    if plot_units is not None:
        fname_str += f"-{plot_units.value.lower().replace('/','_')}"
    if num_bins is not None:
        fname_str += f"-{num_bins}_bins"
    if probability is not None:
        fname_str += f"-{probability:.2f}".replace(".", "_")
    return get_cached_file_base_path() / f"{fname_str}.{extension}"


async def get_location_marker_map(
    location: str | None = "LatLng",
    region: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    extension: str | None = "png",
) -> Path:
    fname_str = f"location-marker-map-{location.lower().replace(' ','_')}"
    if latitude is not None and longitude is not None:
        fname_str += f"-lat_{latitude:.2f}_lng_{longitude:.2f}".replace(".", "_")
    if region is not None:
        fname_str += f"-{region.lower().replace(' ','_')}"
    return get_cached_file_base_path() / f"{fname_str}.{extension}"
