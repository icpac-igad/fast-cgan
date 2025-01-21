from pydantic import BaseModel
from show_forecasts.constants import COLOR_SCHEMES, COUNTRY_NAMES

from fastcgan.jobs.stubs import cgan_model_literal
from fastcgan.tools.constants import GAN_MODELS
from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    PrecipitationUnit,
    ValidStartTime,
)


class BaseForecastParams(BaseModel):
    model: cgan_model_literal | None = GAN_MODELS[0]["name"]
    mask_area: str | None = COUNTRY_NAMES[0]
    forecast_date: str | None = None
    plot_units: PrecipitationUnit | None = PrecipitationUnit.hour6


class CustomStyleForecastProduct(BaseForecastParams):
    color_style: str | None = COLOR_SCHEMES[0]


class OpenIfsParams(CustomStyleForecastProduct):
    vis_param: IfsDataParameter | None = IfsDataParameter.tp


class BaseGanForecastParams(CustomStyleForecastProduct):
    start_time: ValidStartTime | None = ValidStartTime.combine


class GanForecastParams(BaseGanForecastParams):
    acc_time: AccumulationTime | None = AccumulationTime.hour6


class GanEnsembleParams(CustomStyleForecastProduct):
    max_ens_plots: int | None = 10


class GanThresholdChanceParams(CustomStyleForecastProduct):
    threshold: float | None = 5
    show_percentages: bool | None = False


class GanEnsembleHistogramParams(BaseForecastParams):
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    num_bins: int | None = 10
    probability: float | None = None
