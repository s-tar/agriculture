from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from src.domain.exceptions import InvalidGeometryError


class GeometryType(StrEnum):
    POLYGON = "Polygon"


class Point:
    def __init__(self, lon: float, lat: float):
        if lon > 180 or lon < -180:
            raise InvalidGeometryError("Longitude must be between 180 and -180")
        if lat > 90 or lat < -90:
            raise InvalidGeometryError("Latitude must be between 90 and -90")
        self.lon = lon
        self.lat = lat


@dataclass
class Geometry:
    type: GeometryType
    coordinates: list[Point]


@dataclass
class GeometryDetailed(Geometry):
    is_valid: bool
    area_ha: Decimal
