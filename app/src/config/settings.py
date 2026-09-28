from enum import Enum

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
    AREA_MIN_SIZE: float = 0.1


settings = Settings()  # type: ignore
