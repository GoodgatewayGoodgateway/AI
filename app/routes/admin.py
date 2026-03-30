import asyncio
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from app.database import reset_table_auto_increment

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_admin_key(x_admin_key: str = Header(..., description="관리자 API Key. .env의 ADMIN_SECRET_KEY 값")):
    """X-Admin-Key 헤더로 관리자 인증. 일치하지 않으면 403 반환."""
    secret = os.getenv("ADMIN_SECRET_KEY")
    if not secret:
        raise HTTPException(status_code=500, detail="서버에 ADMIN_SECRET_KEY가 설정되지 않았습니다.")
    if x_admin_key != secret:
        raise HTTPException(status_code=403, detail="Forbidden: 올바르지 않은 Admin Key입니다.")


@router.post(
    "/admin/reset/{table}",
    summary="테이블 초기화 (AUTO_INCREMENT 리셋)",
    description=(
        "테이블 데이터를 삭제하고 AUTO_INCREMENT를 1로 초기화합니다.\n\n"
        "**인증 필수:** `X-Admin-Key` 헤더에 관리자 키를 포함해야 합니다.\n\n"
        "허용된 테이블: `listings`, `favorites`\n\n"
        "listings 테이블은 favorites에서 참조 중인 행을 보호합니다.\n\n"
        "**주의:** 삭제된 데이터는 복구할 수 없습니다."
    ),
    response_description="초기화 결과 (삭제 수, 보호 수, AUTO_INCREMENT)",
    dependencies=[Depends(verify_admin_key)],
)
async def reset_table(table: str):
    try:
        result = await asyncio.to_thread(reset_table_auto_increment, table)
        logger.info(f"[테이블 초기화] {table} 완료")
        return result
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"[테이블 초기화 실패] {e}")
        return {"error": str(e)}
