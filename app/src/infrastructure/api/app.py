from fastapi import APIRouter, FastAPI
from src.config.settings import get_settings
from src.infrastructure.api.routers import fields
from starlette.middleware.cors import CORSMiddleware


def setup_app():
    settings = get_settings()
    app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.BASE_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = APIRouter(prefix="/api")

    router.include_router(fields.router)

    app.include_router(router)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
