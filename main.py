from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # ✅ CORS 추가
from app.routes import housing_detail
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

app = FastAPI()

# ✅ CORS 허용 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 시: ["http://34.122.44.97:8888"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(housing_detail.router, prefix="/api", tags=["Housing Detail"])

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST")
    port = int(os.getenv("PORT"))

    uvicorn.run("main:app", host=host, port=port, reload=True)
