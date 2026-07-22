"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.config import settings
from app.middleware import ClinicGateMiddleware


app: FastAPI = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(ClinicGateMiddleware)


@app.get("/")
async def root() -> dict[str, str]:
    """Return a basic service status response."""

    return {"status": "ok", "service": settings.APP_NAME}