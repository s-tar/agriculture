from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..value_objects.field_id import FieldId
from ..value_objects.geometry import Geometry


@dataclass(frozen=True, slots=True)
class Field:
    id: FieldId
    name: str
    owner_name: str
    crop_name: str
    area_ha: Decimal
    geometry: Geometry
    created_at: datetime
    updated_at: datetime
