from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class GeometryType(StrEnum):
    polygon = "Polygon"


@dataclass
class Point:
    lon: float
    lat: float


@dataclass
class Geometry:
    type: GeometryType
    coordinates: list[Point]


@dataclass
class GeometryDetailed(Geometry):
    is_valid: bool
    area_ha: Decimal
