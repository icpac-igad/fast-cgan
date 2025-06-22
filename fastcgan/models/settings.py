from pydantic import BaseModel


class ForecastDate(BaseModel):
    date: str


class GanOutputDate(BaseModel):
    init_date: str
    init_time: int | None = None
    valid_time: int | None = None


class ForecastInitTime(BaseModel):
    hour: str


class ForecastModel(BaseModel):
    name: str
    label: str
    value: str


class MaskArea(BaseModel):
    name: str


class VisualizationColorStyle(BaseModel):
    name: str


class ForecastMap(BaseModel):
    image_url: str
