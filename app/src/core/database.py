from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import Environment
from src.core.config import settings

async_engine = create_async_engine(settings.DATABASE_URL, echo=settings.ENVIRONMENT == Environment.DEVELOPMENT)

async_session_maker = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session():
    async with async_session_maker() as session:
        yield session
