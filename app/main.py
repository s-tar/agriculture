from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import fields

app = FastAPI(title="Agriculture API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
