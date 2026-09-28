import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlmodel
from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped
from sqlmodel import Column, Relationship, SQLModel
from src.config.settings import get_settings

if TYPE_CHECKING:
    from src.infrastructure.repository.sqlmodel.models.crop import Crop
    from src.infrastructure.repository.sqlmodel.models.owner import Owner

settings = get_settings()


class Field(SQLModel, table=True):
    class Config:
        arbitrary_types_allowed = True

    id: uuid.UUID = sqlmodel.Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = sqlmodel.Field(foreign_key="owner.id")
    crop_id: uuid.UUID = sqlmodel.Field(foreign_key="crop.id")

    owner: Mapped["Owner"] = Relationship(back_populates="fields")
    crop: Mapped["Crop"] = Relationship(back_populates="fields")

    area_ha: Decimal = sqlmodel.Field(index=True)
    geometry: WKBElement = sqlmodel.Field(
        sa_column=Column(Geometry("POLYGON", srid=settings.SRID))
    )
    created_at: datetime = sqlmodel.Field(
        default=func.now(),
        sa_column_kwargs={
            "default": func.now(),
            "server_default": func.now(),
        },
    )
    updated_at: datetime = sqlmodel.Field(
        default=func.now(),
        sa_column_kwargs={
            "default": func.now(),
            "server_default": func.now(),
            "onupdate": func.now(),
        },
    )

    __table_args__ = (Index("idx_field_geometry", "geometry", postgresql_using="gist"),)
