from decimal import Decimal
from typing import Protocol

from ..entities.field import Field
from ..value_objects.distance import Distance
from ..value_objects.geometry import Geometry, GeometryDetailed


class FieldRepository(Protocol):
    async def create(
        self,
        name: str,
        owner_name: str,
        crop_name: str,
        geometry: Geometry,
    ) -> Field: ...

    async def get(
        self,
        field_id: str,
    ) -> Field | None: ...

    async def get_many(
        self,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Field]: ...

    async def count(
        self,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
    ) -> int: ...

    async def find_by_point(
        self,
        lon: float,
        lat: float,
    ) -> list[tuple[Field, Distance]]: ...

    async def get_geometry_details(self, geometry: Geometry) -> GeometryDetailed: ...
