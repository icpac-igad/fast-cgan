from pydantic import BaseModel
from show_forecasts.constants import COUNTRY_NAMES

from fastcgan.jobs.stubs import cgan_model_literal
from fastcgan.tools.constants import GAN_MODELS
from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    InitializationTime,
    MapColorScheme,
    PrecipitationUnit,
    ValidityTime,
)


class OpenIfsParams(BaseModel):
    mask_area: str | None = COUNTRY_NAMES[0]
    forecast_date: str | None = None
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day
    vis_param: IfsDataParameter | None = IfsDataParameter.tp
    color_style: MapColorScheme | None = MapColorScheme.icpac


class GanForecastParams(BaseModel):
    model: cgan_model_literal | None = GAN_MODELS[0]["name"]
    mask_area: str | None = COUNTRY_NAMES[0]
    forecast_date: str | None = None
    init_time: InitializationTime | None = InitializationTime.midnight
    acc_time: AccumulationTime | None = AccumulationTime.half_day
    valid_time: ValidityTime | None = None
    plot_units: PrecipitationUnit | None = PrecipitationUnit.half_day
    color_style: MapColorScheme | None = MapColorScheme.icpac


class GanEnsembleParams(GanForecastParams):
    max_ens_plots: int | None = 10


class GanThresholdChanceParams(GanForecastParams):
    threshold: float | None = 5
    show_percentages: bool | None = False
