from enum import Enum


class IfsDataParameter(Enum):
    tp = "Total precipitation"
    sp = "Surface pressure"
    msl = "Pressure at mean sea level"
    t2m = "Two metre temperature"
    wind = "Wind speed"
    ro = "Surface runoff water"


class PrecipitationUnit(Enum):
    hour = "mm/h"
    half_day = "mm/6h"
    day = "mm/day"
    # week = "mm/week"


class AccumulationTime(Enum):
    half_day = "06h"
    day = "24h"


class MapColorScheme(Enum):
    icpac = "ICPAC"
    kmd = "KMD"
    emi = "EMI"
    default = "Default"


class InitializationTime(Enum):
    midnight = "00h"
    morning = "06h"
    midday = "12h"
    evening = "18h"


class ValidityTime(Enum):
    plus6h = "06h"
    plus30h = "30h"
    plus36h = "36h"
    plus42h = "42h"
    plus48h = "48h"
    plus54h = "54h"
    plus78h = "78h"
    plus102h = "102h"
    plus126h = "126h"
    plus150h = "150h"
    all_steps = "all"


class RouterTag(Enum):
    general = "Generic Routes"
    settings = "Settings Payload"
    gan = "cGAN Forecasts"
    open_ifs = "Open IFS Forecasts"
