from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.clinic_gate import ClinicGateMiddleware
from app.api.v1.router import api_router

app = FastAPI(
    title="AV Suite Backend Foundation",
    version="0.1.0",
)

app.add_middleware(ClinicGateMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
