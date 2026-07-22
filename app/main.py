"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import settings
from app.middleware import ClinicGateMiddleware

app: FastAPI = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(ClinicGateMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Return a basic service status response."""

    return {"status": "ok", "service": settings.APP_NAME}