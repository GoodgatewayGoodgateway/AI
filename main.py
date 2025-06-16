from fastapi import FastAPI
from app.routes import housing_detail

app = FastAPI()

app.include_router(housing_detail.router, prefix="/api", tags=["Housing Detail"])