from decimal import Decimal
from typing import TypeAlias
from uuid import UUID

from geoalchemy2 import Geography, functions
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from sqlmodel import cast, select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.domain.entities.field import Field
from src.domain.repositories.field_repository import FieldRepository
from src.domain.value_objects.distance import Distance
from src.domain.value_objects.geometry import (
    Geometry,
    GeometryDetailed,
)

from .convertors import field_model_to_entity, geometry_to_wkb
from .models.crop import Crop
from .models.crop import Crop as CropModel
from .models.field import Field as FieldModel
from .models.owner import Owner
from .models.owner import Owner as OwnerModel

FieldIdType: TypeAlias = UUID

SQUARE_METES_TO_HECTARE = 0.0001


class SqlModelFieldRepository(FieldRepository):
    def __init__(self, session: AsyncSession, srid: int):
        self.session = session
        self.srid = srid

    async def _parse_id(self, value: str) -> FieldIdType:
        try:
            return UUID(value)
        except ValueError:
            raise ValueError("Invalid Field id format")

    def _apply_filters(
        self,
        statement,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
    ):
        if min_area:
            statement = statement.where(FieldModel.area_ha >= min_area)

        if max_area:
            statement = statement.where(FieldModel.area_ha < max_area)

        if crop_name:
            statement = statement.join(FieldModel.crop).where(Crop.name == crop_name)

        if owner_name:
            statement = statement.join(FieldModel.owner).where(Owner.name == owner_name)

        return statement

    async def _get_or_create_crop(self, name: str) -> CropModel:
        crop = (
            await self.session.exec(select(CropModel).where(CropModel.name == name))
        ).first()
        if not crop:
            crop = CropModel(name=name)
            self.session.add(crop)
            await self.session.flush()
            await self.session.refresh(crop)

        return crop

    async def _get_or_create_owner(self, name: str) -> OwnerModel:
        owner = (
            await self.session.exec(select(OwnerModel).where(OwnerModel.name == name))
        ).first()
        if not owner:
            owner = OwnerModel(name=name)
            self.session.add(owner)
            await self.session.flush()
            await self.session.refresh(owner)

        return owner

    async def get(
        self,
        field_id: str,
    ) -> Field | None:
        field = (
            await self.session.exec(
                select(FieldModel)
                .where(FieldModel.id == field_id)
                .options(joinedload(FieldModel.owner), joinedload(FieldModel.crop)),
            )
        ).first()

        if not field:
            return None

        return field_model_to_entity(field)

    async def find_by_point(
        self,
        lon: float,
        lat: float,
    ) -> list[tuple[Field, Distance]]:
        point_wkt = f"POINT({lon} {lat})"
        point = functions.ST_GeomFromText(point_wkt, self.srid)

        statement = (
            select(
                FieldModel,
                functions.ST_Distance(
                    cast(point, Geography(srid=self.srid)),
                    cast(
                        functions.ST_Centroid(FieldModel.geometry),
                        Geography(srid=self.srid),
                    ),
                ),
            )
        ).where(functions.ST_Contains(FieldModel.geometry, point))

        statement = statement.options(
            joinedload(FieldModel.owner), joinedload(FieldModel.crop)
        )

        result = (await self.session.exec(statement)).all()
        return [
            (field_model_to_entity(field), Distance(distance))
            for field, distance in result
        ]

    async def get_many(
        self,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Field]:
        statement = self._apply_filters(
            statement=select(FieldModel),
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
        )
        statement = statement.limit(limit).offset(offset)

        statement = statement.options(
            joinedload(FieldModel.owner), joinedload(FieldModel.crop)
        )

        result = (await self.session.exec(statement)).all()
        return [field_model_to_entity(field) for field in result]

    async def count(
        self,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
    ) -> int:
        statement = self._apply_filters(
            statement=select(func.count()).select_from(FieldModel),
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
        )

        return (await self.session.exec(statement)).one()

    async def get_geometry_details(self, geometry: Geometry) -> GeometryDetailed:
        geometry_wkb = geometry_to_wkb(geometry, srid=self.srid)
        is_valid, area_m2 = (
            await self.session.exec(
                select(
                    functions.ST_IsValid(geometry_wkb),
                    functions.ST_Area(
                        cast(geometry_wkb, Geography(srid=self.srid)),
                    ),
                ),
            )
        ).one()

        return GeometryDetailed(
            type=geometry.type,
            coordinates=geometry.coordinates,
            is_valid=is_valid,
            area_ha=Decimal(area_m2 * SQUARE_METES_TO_HECTARE),
        )

    async def create(
        self,
        name: str,
        owner_name: str,
        crop_name: str,
        geometry: Geometry,
    ) -> Field:
        crop = await self._get_or_create_crop(crop_name)
        owner = await self._get_or_create_owner(owner_name)
        geometry_wkb = geometry_to_wkb(geometry, srid=self.srid)
        field = FieldModel(
            name=name,
            owner_id=owner.id,
            crop_id=crop.id,
            geometry=geometry_wkb,
            area_ha=functions.ST_Area(
                cast(geometry_wkb, Geography(srid=self.srid)),
            )
            * SQUARE_METES_TO_HECTARE,  # type: ignore
        )
        self.session.add(field)
        await self.session.flush()
        await self.session.refresh(field)

        return field_model_to_entity(field)
