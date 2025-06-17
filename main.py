from fastapi import FastAPI
from app.routes import housing_detail
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

app = FastAPI()

app.include_router(housing_detail.router, prefix="/api", tags=["Housing Detail"])

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST")
    port = int(os.getenv("PORT"))

    uvicorn.run("main:app", host=host, port=port, reload=True)