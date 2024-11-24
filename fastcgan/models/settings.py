from pydantic import BaseModel


class ForecastDate(BaseModel):
    date: str


class MaskArea(BaseModel):
    name: str


class VisualizationColorStyle(BaseModel):
    name: str


class ForecastMap(BaseModel):
    image_url: str
