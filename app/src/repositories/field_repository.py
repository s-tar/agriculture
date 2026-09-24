from decimal import Decimal

from geoalchemy2 import functions
from geoalchemy2 import Geography
from geoalchemy2 import Geometry
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlmodel import cast
from sqlmodel import select

from src.core.config import settings
from src.core.database import async_session_maker
from src.models.crop import Crop
from src.models.field import Field
from src.models.owner import Owner
from src.repositories.base_repository import BaseRepository
from src.schemas.field import FieldWithDistanceToPoint
from src.schemas.field import GeometryValidation


class FieldRepositoryClass(BaseRepository[Field]):
    def __init__(self):
        super().__init__(Field)

    async def get_geometry_validation(self, geometry: Geometry) -> GeometryValidation:
        async with async_session_maker() as session:
            is_valid, area = (await session.exec(
                select(
                    functions.ST_IsValid(geometry),
                    functions.ST_Area(cast(geometry, Geography(srid=settings.SRID))),
                ),
            )).one()
            return GeometryValidation(is_valid=is_valid, area=area)

    def apply_filters(
        self,
        statement,
        crop_name: str = None,
        owner_name: str = None,
        min_area: Decimal = None,
        max_area: Decimal = None,
    ):
        if min_area:
            statement = statement.where(Field.area_ha >= min_area)

        if max_area:
            statement = statement.where(Field.area_ha < max_area)

        if crop_name:
            statement = statement.join(Crop).where(Crop.name == crop_name)

        if owner_name:
            statement = statement.join(Owner).where(Owner.name == owner_name)

        return statement

    async def get_by_id(self, field_id: int) -> Field | None:
        async with async_session_maker() as session:
            return (await session.exec(
                select(Field)
                .where(Field.id == field_id)
                .options(joinedload(Field.owner), joinedload(Field.crop)),
            )).first()

    async def get_list(
        self,
        crop_name: str = None,
        owner_name: str = None,
        min_area: Decimal = None,
        max_area: Decimal = None,
        limit: int = 10,
        offset: int = 0,
    ) -> Field | []:
        statement = self.apply_filters(
            statement=select(Field),
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
        )
        statement = statement.limit(limit).offset(offset)

        statement = statement.options(joinedload(Field.owner), joinedload(Field.crop))

        async with async_session_maker() as session:
            return (await session.exec(statement)).all()

    async def count(
        self,
        crop_name: str = None,
        owner_name: str = None,
        min_area: Decimal = None,
        max_area: Decimal = None,
    ) -> int:
        statement = self.apply_filters(
            statement=select(func.count(self.table_model.id)),
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
        )

        async with async_session_maker() as session:
            return (await session.exec(statement)).one()

    async def find_by_point(
        self,
        lon: float,
        lat: float,
    ) -> list[FieldWithDistanceToPoint]:
        point_wkt = f"POINT({lon} {lat})"
        point = functions.ST_GeomFromText(point_wkt, settings.SRID)

        statement = (
            select(
                Field,
                functions.ST_Distance(
                    cast(point, Geography(srid=settings.SRID)),
                    cast(functions.ST_Centroid(Field.geometry), Geography(srid=settings.SRID)),
                ),
            )
        ).where(functions.ST_Contains(Field.geometry, point))

        statement = statement.options(joinedload(Field.owner), joinedload(Field.crop))

        async with async_session_maker() as session:
            result = (await session.exec(statement)).all()
            return [
                FieldWithDistanceToPoint(
                    field=field,
                    distance_to_center_m=distance,
                )
                for field, distance in result
            ]


FieldRepository = FieldRepositoryClass()
