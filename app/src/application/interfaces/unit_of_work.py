from typing import Protocol

from src.domain.repositories.field_repository import FieldRepository


class UnitOfWork(Protocol):
    fields: FieldRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args): ...

    async def commit(self): ...

    async def rollback(self): ...
