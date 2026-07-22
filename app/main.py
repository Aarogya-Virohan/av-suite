"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.middleware import ClinicGateMiddleware

app: FastAPI = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# Production security and compression middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ClinicGateMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Return a basic service status response."""

    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/health")
@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """Health probe endpoint for Railway and cloud load balancers."""

    return {"status": "healthy", "service": settings.APP_NAME}