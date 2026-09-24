from abc import ABC
from typing import Any

from sqlalchemy import func
from sqlmodel import select

from src.core.database import async_session_maker


class BaseRepository[T](ABC):
    def __init__[T](self, table_model: type[T]):
        self.table_model = table_model

    async def create(self, **data: dict[str, Any]) -> T:
        async with async_session_maker() as session:
            entity = self.table_model(**data)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)

            return entity

    async def update(self, entity_id: int, data: dict[str, Any]) -> T | None:
        async with async_session_maker() as session:
            entity = await self.get_by_id(entity_id)
            if not entity:
                return None

            entity.sqlmodel_update(data)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)

            return entity

    async def get_by_id(self, entity_id: int) -> T:
        async with async_session_maker() as session:
            return (await session.exec(select(self.table_model).where(self.table_model.id == entity_id))).first()

    async def get(self, *filters) -> T:
        async with async_session_maker() as session:
            statement = select(self.table_model).where(*filters)
            return (await session.exec(statement)).first()

    async def get_list(
        self,
        *filters,
        offset: int | None = None,
        limit: int | None = None,
        order_by: list = None,
    ) -> list[T]:
        async with async_session_maker() as session:
            statement = select(self.table_model).where(*filters)

            if offset:
                statement = statement.offset(offset)

            if limit:
                statement = statement.limit(limit)

            if order_by:
                statement = statement.order_by(*order_by)

            return (await session.exec(statement)).all()

    async def delete(self, entity_id: int) -> int | None:
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        async with async_session_maker() as session:
            await session.delete(entity)
            await session.commit()

            return entity.id

    async def count(
        self,
        *filters,
        offset: int | None = None,
        limit: int | None = None,
    ) -> int:
        async with async_session_maker() as session:
            statement = select(func.count(self.table_model.id)).where(*filters)

            if offset:
                statement = statement.offset(offset)

            if limit:
                statement = statement.limit(limit)
            return (await session.exec(statement)).one()

    async def exists(
        self,
        *filters,
    ) -> bool:
        async with async_session_maker() as session:
            statement = select(self.table_model.id).where(*filters)
            return bool((await session.exec(statement)).first())
