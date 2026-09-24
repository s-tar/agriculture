import uuid
from typing import TYPE_CHECKING

import sqlmodel
from sqlmodel import Relationship
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from src.models.field import Field


class Owner(SQLModel, table=True):
    id: uuid.UUID = sqlmodel.Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = sqlmodel.Field(unique=True, index=True)

    fields: list["Field"] = Relationship(back_populates="owner")
