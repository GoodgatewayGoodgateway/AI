import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, Query
from app.database import get_market_trend_db
from app.services.geolocation import address_to_coords
from app.routes._shared import TYPES_QUERY_DESC
from src.classes import NLocation
from src.util import get_article_listings, get_complex_listings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/market/stats",
    summary="지역 시세 통계 조회",
    description=(
        "지역명을 입력하면 매물 수, 타입별 평균 가격·면적, 가격 범위를 반환합니다.\n\n"
        "Response: total_count, by_type{ count, avg_price, avg_area_m2 }, price_range{ min, max }"
    ),
    response_description="지역 시세 통계",
)
async def get_market_stats(
    query: str = Query(..., description="지역명 또는 주소. 예) 강남구"),
    type: Optional[str] = Query(None, description="매물 유형 필터 (선택). 예) 원룸"),
):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(query)
        loc = NLocation(lat, lng)
        type_filter = [type] if type else None

        results = await asyncio.gather(
            get_article_listings(loc, pages=2, estate_types=type_filter),
            get_complex_listings(loc, estate_types=type_filter),
            return_exceptions=True,
        )

        listings = []
        for r in results:
            if not isinstance(r, Exception):
                listings.extend(r)

        if not listings:
            return {"area": query, "total_count": 0, "by_type": {}, "price_range": {"min": 0, "max": 0}}

        by_type: dict = {}
        for l in listings:
            t = l.get("type", "기타")
            if t not in by_type:
                by_type[t] = {"count": 0, "total_price": 0, "total_area": 0.0}
            by_type[t]["count"] += 1
            by_type[t]["total_price"] += l.get("price", 0)
            by_type[t]["total_area"] += l.get("area", 0.0)

        by_type_stats = {
            t: {
                "count": v["count"],
                "avg_price": int(v["total_price"] / v["count"]) if v["count"] else 0,
                "avg_area_m2": round(v["total_area"] / v["count"], 1) if v["count"] else 0.0,
            }
            for t, v in by_type.items()
        }

        prices = [l.get("price", 0) for l in listings if l.get("price")]
        logger.info(f"[시세 통계] {query} {len(listings)}건 {time.perf_counter() - start:.2f}초")
        return {
            "area": query,
            "total_count": len(listings),
            "by_type": by_type_stats,
            "price_range": {"min": min(prices) if prices else 0, "max": max(prices) if prices else 0},
        }
    except Exception as e:
        logger.error(f"[시세 통계 실패] {e}")
        return {"error": str(e)}


@router.get(
    "/market/trend",
    summary="지역 가격 트렌드 조회",
    description=(
        "지역명과 유형을 입력하면 날짜별 평균 환산가격 추이를 반환합니다.\n\n"
        "데이터는 listings/search 또는 listings/all 조회 시 DB에 축적됩니다."
    ),
    response_description="날짜별 평균 가격 트렌드",
)
async def get_market_trend(
    query: str = Query(..., description="지역명. 예) 마포구"),
    type: Optional[str] = Query(None, description="매물 유형 필터 (선택). 예) 원룸"),
):
    try:
        rows = await asyncio.to_thread(get_market_trend_db, query, type)
        trend = [
            {"date": str(r["date"]), "avg_price": int(r["avg_price"] or 0), "count": r["count"]}
            for r in rows
        ]
        return {"area": query, "type": type, "trend": trend}
    except Exception as e:
        logger.error(f"[트렌드 조회 실패] {e}")
        return {"error": str(e)}
