from pydantic import BaseModel, Field

from fastcgan.tools.enums import (
    AccumulationTime,
    IfsDataParameter,
    PrecipitationUnit,
    ValidStartTime,
)


class ForecastDate(BaseModel):
    date: str


class DataParams(BaseModel):
    mask_area: str | None = Field(
        default="",
        json_schema_extra={
            "search_url": "/api/forecast/mask-areas",
            "placeholder": "Clip to Region of Interest...",
        },
        title="Select Region Name",
        description="useful for masking out the forecast to a specific area of interest",
    )
    data_date: str | None = Field(
        default="",
        json_schema_extra={
            "search_url": "/api/forecast/data-dates",
            "placeholder": "Change Data Date...",
        },
        title="Select Forecast Initialization Date",
        description="this is the date when the forecast was initialized which denote start of lead time",
    )
    vis_param: IfsDataParameter = Field(
        default=IfsDataParameter.tp,
        title="Select Data Variable",
        description="Value selected denotes forecast data variable that will be plotted",
    )
    color_style: str | None = Field(
        default="",
        json_schema_extra={
            "search_url": "/api/forecast/color-styles",
            "placeholder": "Change Color Style...",
        },
        title="Select Color Style",
        description="color style used to generate forecast visualization maps and graphs",
    )
    plot_units: PrecipitationUnit = Field(
        default=PrecipitationUnit.hour6,
        title="Select Accumulation Unit",
        description="Precipitation value is prorated to selected accumulation unit",
    )


class IfsParams(DataParams):
    show_ensemble: bool | None = Field(
        default=True,
        title="Show Ensemble Members",
        description="A switch to toggle visibility of ensemble members visualization",
    )


class cGANParams(DataParams):
    acc_time: AccumulationTime = Field(
        default=AccumulationTime.hour6,
        title="Select Accumulation Time",
        description="Amount of precipitation recorded is prorated to accumulation time selected",
    )
    start_time: ValidStartTime = Field(
        default=ValidStartTime.six,
        title="Select Valid Forecast Start Hour",
        description="start hour when the forecast is valid. Value depends on forecast time range",
    )


class cGANEnsembleMembers(BaseModel):
    # show_ensemble: bool = Field(
    #     default=False,
    #     title="Show Ensemble Members",
    #     description="A switch to toggle visibility of ensemble members visualization",
    # )
    max_ensemble_plots: int | None = Field(
        default=10,
        title="Maximum number of Ensemble Plots",
        description="Specify maximum number of ensemble member plots to be generated",
    )


class cGANThresholdChance(BaseModel):
    # thres_chance: bool = Field(
    #     default=False,
    #     title="Show threshold exceedence chance",
    #     description="Enables plotting of threshold exceedence plots",
    # )
    threshold: float = Field(
        default=5,
        title="Threshold Value",
        description="Threshold value to be evaluated in plotting units specified",
    )
    show_percentages: bool = Field(
        default=False,
        title="Show percentages",
        description="Enables reporting of threshold exceedence in percentages instead of categorical classes",
    )


class cGANHistogram(BaseModel):
    # show_hist: bool = Field(
    #     default=False,
    #     title="Show cGAN Location Histogram",
    #     description="Enables plotting of histogram plots for a given location",
    # )
    location: str | None = Field(
        default="",
        json_schema_extra={
            "search_url": "/api/forecast/locations",
            "placeholder": "Select location name...",
        },
        title="Select Location Name",
        description="Location to be used for histogram plotting",
    )
    latitude: float | None = Field(
        default=0.0,
        title="Optional latiude in degrees north",
        description="If specified along with a longitude, this location is used instead of any the pre-defined options "
        + "on the locations dropdown",
    )
    longitude: float | None = Field(
        default=0.0,
        title="Optional longitude in degrees north",
        description="If specified along with a latitude, this location is used instead of any the pre-defined options "
        + "on the locations dropdown",
    )
    probability: float | None = Field(
        default=0.0,
        title="Precipitation Certainity Level",
        description="Plot a line indicating the amount of rain that will be exceeded with a given probability.",
    )
    num_bins: int | None = Field(
        default=10,
        title="Number of Histogram Bins",
        description="Number of evenly spaced bins in the histogram",
    )
