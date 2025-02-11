from enum import Enum

# from show_forecasts.constants import ACCUMULATION_UNITS


class IfsDataParameter(Enum):
    tp = "Total precipitation"
    sp = "Surface pressure"
    msl = "Pressure at mean sea level"
    t2m = "Two metre temperature"
    wind = "Wind speed"
    ro = "Surface runoff water"


class PrecipitationUnit(Enum):
    hour = "mm/h"
    hour6 = "mm/6h"
    day = "mm/day"
    week = "mm/week"


class AccumulationTime(Enum):
    hour6 = "6h"
    day = "24h"


class ValidStartTime(Enum):
    six = "6"
    one_two = "12"
    one_eight = "18"
    zero = "0"


class RouterTag(Enum):
    general = "Generic Routes"
    settings = "Settings Payload"
    forecast = "Forecast Products"
