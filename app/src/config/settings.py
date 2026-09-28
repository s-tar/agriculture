from decimal import Decimal
from enum import Enum

from anyio.functools import lru_cache
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    ENVIRONMENT: Environment
    DATABASE_URL: str

    VERSION: str
    PROJECT_NAME: str
    BASE_URL: str

    SRID: int = 4326
    AREA_MIN_SIZE: Decimal = Decimal("0.1")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore
