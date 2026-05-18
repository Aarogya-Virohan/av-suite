from fastapi import FastAPI

from app.api.v1.posture import router as posture_router

app = FastAPI()

app.include_router(posture_router)
