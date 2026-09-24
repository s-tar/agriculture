import uuid
from datetime import datetime
from decimal import Decimal

import sqlmodel
from geoalchemy2 import Geometry
from sqlalchemy import func
from sqlalchemy import Index
from sqlmodel import Column
from sqlmodel import Relationship
from sqlmodel import SQLModel

from src.models.crop import Crop
from src.models.owner import Owner


class Field(SQLModel, table=True):
    id: uuid.UUID = sqlmodel.Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    owner_id: uuid.UUID = sqlmodel.Field(foreign_key="owner.id")
    crop_id: uuid.UUID = sqlmodel.Field(foreign_key="crop.id")

    owner: Owner = Relationship(back_populates="fields")
    crop: Crop = Relationship(back_populates="fields")

    area_ha: Decimal = sqlmodel.Field(index=True)
    geometry: str = sqlmodel.Field(sa_column=Column(Geometry('POLYGON', srid=4326)))
    created_at: datetime = sqlmodel.Field(sa_column_kwargs={
        "default": func.now(),
        "server_default": func.now(),
    })
    updated_at: datetime = sqlmodel.Field(sa_column_kwargs={
        "default": func.now(),
        "server_default": func.now(),
        "onupdate": func.now(),
    })

    __table_args__ = (
        Index("idx_field_geometry", "geometry", postgresql_using="gist"),
    )
