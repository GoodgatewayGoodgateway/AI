from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import housing_detail
from app.services.geolocation import set_shared_client, close_shared_client
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import httpx
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient()
    set_shared_client(client)
    yield
    await close_shared_client()

app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(housing_detail.router, prefix="/api", tags=["Housing Detail"])

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
