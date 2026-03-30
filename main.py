from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.geolocation import set_shared_client, close_shared_client
from app.database import init_db, reset_table_auto_increment
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import asyncio
import httpx
import logging
import os

# 라우터 — 도메인별 분리
from app.routes import analysis, listings, market, recommend, favorites, admin

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESET_INTERVAL_SECONDS = 10 * 60  # 10분


async def _periodic_reset():
    """10분마다 listings 테이블 AUTO_INCREMENT 초기화"""
    while True:
        await asyncio.sleep(RESET_INTERVAL_SECONDS)
        try:
            result = await asyncio.to_thread(reset_table_auto_increment, "listings")
            logger.info(f"[주기적 초기화] listings {result['deleted_count']}건 삭제, AUTO_INCREMENT=1")
        except Exception as e:
            logger.error(f"[주기적 초기화 실패] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 초기화 — DB 연결 실패해도 서버는 기동 유지
    try:
        init_db()
        result = await asyncio.to_thread(reset_table_auto_increment, "listings")
        logger.info(f"[서버 시작] listings 초기화 완료 ({result['deleted_count']}건 삭제, AUTO_INCREMENT=1)")
    except Exception as e:
        logger.error(f"[서버 시작 초기화 실패] {e} — DB 없이 기동 계속")

    client = httpx.AsyncClient()
    set_shared_client(client)

    reset_task = asyncio.create_task(_periodic_reset())

    yield

    # 종료 시 초기화
    reset_task.cancel()
    try:
        result = await asyncio.to_thread(reset_table_auto_increment, "listings")
        logger.info(f"[서버 종료] listings 초기화 완료 ({result['deleted_count']}건 삭제, AUTO_INCREMENT=1)")
    except Exception as e:
        logger.error(f"[서버 종료 초기화 실패] {e}")

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

# ── 헬스체크 (Railway 헬스체크 경로) ──────────────────────
@app.get("/health", tags=["헬스체크"])
def health_check():
    return {"status": "ok"}

# ── 라우터 등록 ────────────────────────────────────────────
app.include_router(analysis.router,   prefix="/api", tags=["분석"])
app.include_router(listings.router,   prefix="/api", tags=["매물 검색"])
app.include_router(market.router,     prefix="/api", tags=["시세 분석"])
app.include_router(recommend.router,  prefix="/api", tags=["추천"])
app.include_router(favorites.router,  prefix="/api", tags=["즐겨찾기"])
app.include_router(admin.router,      prefix="/api", tags=["관리"])

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8888))
    uvicorn.run("main:app", host=host, port=port, reload=True)
