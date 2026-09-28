from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.use_cases.commands.create_field import CreateFieldHandler
from src.application.use_cases.queries.find_fields_by_point import (
    GetFieldByPointHandler,
)
from src.application.use_cases.queries.get_field import GetFieldHandler
from src.application.use_cases.queries.list_fields import ListFieldsHandler
from src.config.settings import settings
from src.infrastructure.repository.sqlmodel.database import get_session
from src.infrastructure.repository.sqlmodel.unit_of_work import SqlModelUnitOfWork


def get_unit_of_work(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnitOfWork:
    return SqlModelUnitOfWork(session, srid=settings.SRID)


def get_get_field_handler(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> GetFieldHandler:
    return GetFieldHandler(uow=uow)


def get_get_field_by_point_handler(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> GetFieldByPointHandler:
    return GetFieldByPointHandler(uow=uow)


def get_list_fields_handler(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ListFieldsHandler:
    return ListFieldsHandler(uow=uow)


def get_create_field_handler(
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> CreateFieldHandler:
    return CreateFieldHandler(uow=uow)
