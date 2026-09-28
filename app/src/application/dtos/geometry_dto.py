from dataclasses import dataclass


@dataclass
class PointDTO:
    lon: float
    lat: float


@dataclass
class GeometryDTO:
    type: str
    coordinates: list[PointDTO]
