from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_upload import router as upload_router

app = FastAPI(title="InsightFlow AI")

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(analysis_router)
