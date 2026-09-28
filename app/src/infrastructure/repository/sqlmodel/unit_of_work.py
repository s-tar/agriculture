from sqlmodel.ext.asyncio.session import AsyncSession
from src.application.interfaces.unit_of_work import UnitOfWork
from src.infrastructure.repository.sqlmodel.field_repository import (
    SqlModelFieldRepository,
)


class SqlModelUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession, srid: int):
        self.session = session
        self.fields = SqlModelFieldRepository(self.session, srid=srid)

    async def __aenter__(self): ...

    async def __aexit__(self, exc_type, *args):
        if exc_type is not None:
            await self.rollback()
            return False

        await self.commit()
        return True

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
