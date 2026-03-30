import asyncio
import logging

from fastapi import APIRouter, Body, Query
from app.schemas import FavoriteRequest
from app.database import add_favorite, get_favorites_db, delete_favorite

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/favorites",
    summary="즐겨찾기 추가",
    description=(
        "매물 ID를 즐겨찾기에 추가합니다.\n\n"
        "이미 즐겨찾기된 매물이면 error를 반환합니다."
    ),
    response_description="생성된 즐겨찾기 항목",
)
async def create_favorite(data: FavoriteRequest = Body(...)):
    try:
        result = await asyncio.to_thread(add_favorite, data.user_id, data.listing_id)
        if result is None:
            return {"error": "이미 즐겨찾기에 추가된 매물입니다."}
        return result
    except Exception as e:
        logger.error(f"[즐겨찾기 추가 실패] {e}")
        return {"error": str(e)}


@router.get(
    "/favorites/{user_id}",
    summary="즐겨찾기 목록 조회",
    description="user_id에 해당하는 즐겨찾기 매물 목록을 반환합니다. (listings 테이블과 JOIN)",
    response_description="즐겨찾기 매물 목록",
)
async def list_favorites(user_id: str):
    try:
        rows = await asyncio.to_thread(get_favorites_db, user_id)
        return {"favorites": rows}
    except Exception as e:
        logger.error(f"[즐겨찾기 조회 실패] {e}")
        return {"error": str(e)}


@router.delete(
    "/favorites/{favorite_id}",
    summary="즐겨찾기 삭제",
    description=(
        "즐겨찾기 항목을 삭제합니다.\n\n"
        "- favorite_id: 즐겨찾기 항목 ID\n"
        "- user_id (query): 본인 항목만 삭제 가능"
    ),
    response_description="삭제 결과",
)
async def remove_favorite(
    favorite_id: int,
    user_id: str = Query(..., description="사용자 식별자"),
):
    try:
        deleted = await asyncio.to_thread(delete_favorite, favorite_id, user_id)
        if not deleted:
            return {"error": "해당 즐겨찾기 항목이 없거나 권한이 없습니다."}
        return {"deleted": True, "favorite_id": favorite_id}
    except Exception as e:
        logger.error(f"[즐겨찾기 삭제 실패] {e}")
        return {"error": str(e)}
