from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.posture import router as posture_router

app = FastAPI(title="AV Suite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posture_router)
