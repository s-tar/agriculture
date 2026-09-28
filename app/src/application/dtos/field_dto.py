from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .distance_dto import DistanceDTO
from .geometry_dto import GeometryDTO


@dataclass
class FieldIdDTO:
    id: str


@dataclass
class FieldDTO:
    id: str
    name: str
    owner_name: str
    crop_name: str
    area_ha: Decimal


@dataclass
class FieldDetailedDTO(FieldDTO):
    geometry: GeometryDTO
    created_at: datetime
    updated_at: datetime


@dataclass
class FieldWithDistanceToCenterDTO(FieldDTO):
    distance_to_center_m: DistanceDTO
