import uuid
import pydantic

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator
from pydantic import BaseModel

from src.models.field import Field

RoundedFloat = Annotated[float, AfterValidator(lambda v: round(v, 1))]


class GeometryType(StrEnum):
    POLYGON = "Polygon"


class GeoPoint(BaseModel):
    lon: float
    lat: float


class GeometrySchema(BaseModel):
    type: GeometryType
    coordinates: list[list[tuple[float, float]]]


class ListFieldResponse(BaseModel):
    id: uuid.UUID
    name: str
    area_ha: RoundedFloat
    crop: str
    owner: str


class FindByPointFieldResponse(ListFieldResponse):
    distance_to_center_m: RoundedFloat


class FindByPointResponse(BaseModel):
    query_point: GeoPoint
    fields: list[FindByPointFieldResponse]
    query_time_ms: RoundedFloat


class FieldResponse(BaseModel):
    id: uuid.UUID
    name: str
    area_ha: RoundedFloat
    geometry: GeometrySchema
    crop: str
    owner: str
    created_at: datetime


class FieldCreateData(BaseModel):
    name: str = pydantic.Field(min_length=1, max_length=250)
    geometry: GeometrySchema
    crop: str = pydantic.Field(min_length=1, max_length=250)
    owner: str = pydantic.Field(min_length=1, max_length=250)


class GeometryValidation(BaseModel):
    is_valid: bool
    area: float


class FieldWithDistanceToPoint(BaseModel):
    distance_to_center_m: float
    field: Field
