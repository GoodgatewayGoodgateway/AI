import asyncio
import logging
import time

from fastapi import APIRouter, Body
from app.schemas import RecommendRequest
from app.database import save_listings
from app.services.geolocation import address_to_coords
from app.routes._shared import pyeong_to_m2, to_pyeong, TYPES_QUERY_DESC
from src.classes import NLocation
from src.util import get_article_listings, get_complex_listings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/recommend",
    summary="조건 기반 추천 매물 조회",
    description=(
        "예산·면적·유형 조건을 입력하면 해당 지역에서 가성비가 높은 매물을 추천합니다.\n\n"
        "정렬 기준: 단위면적(㎡)당 환산가격 낮을수록 상위"
    ),
    response_description="조건 기반 추천 매물 목록",
)
async def recommend_listings(data: RecommendRequest = Body(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(data.query)
        loc = NLocation(lat, lng)
        type_filter = data.preferred_types or None

        results = await asyncio.gather(
            get_article_listings(loc, pages=2, estate_types=type_filter),
            get_complex_listings(loc, estate_types=type_filter),
            return_exceptions=True,
        )

        listings = []
        for r in results:
            if not isinstance(r, Exception):
                listings.extend(r)

        min_area_m2 = pyeong_to_m2(data.min_area_pyeong) if data.min_area_pyeong else None

        filtered = [
            l for l in listings
            if (data.max_deposit is None or l.get("deposit", 0) <= data.max_deposit)
            and (data.max_monthly is None or l.get("monthly", 0) <= data.max_monthly)
            and (min_area_m2 is None or l.get("area", 0) >= min_area_m2)
        ]

        def price_per_m2(l):
            return l.get("price", 0) / (l.get("area") or 1)

        sorted_listings = sorted(filtered, key=price_per_m2)[:data.top_n]
        saved = await asyncio.to_thread(save_listings, sorted_listings, data.query)

        recommendations = [
            {
                "id": s.get("id"),
                "address": s.get("address"),
                "area_m2": round(s.get("area", 0), 1),
                "area_pyeong": to_pyeong(s.get("area", 0)),
                "deposit": s.get("deposit"),
                "monthly": s.get("monthly"),
                "price": s.get("price"),
                "price_per_m2": round(price_per_m2(s), 1),
                "type": s.get("type"),
                "lat": s.get("lat"),
                "lng": s.get("lng"),
            }
            for s in saved
        ]

        logger.info(f"[추천 매물] {data.query} {len(filtered)}건 중 {len(recommendations)}건 반환 {time.perf_counter() - start:.2f}초")
        return {"query": data.query, "total_filtered": len(filtered), "recommendations": recommendations}
    except Exception as e:
        logger.error(f"[추천 매물 실패] {e}")
        return {"error": str(e)}
