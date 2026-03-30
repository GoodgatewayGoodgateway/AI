import asyncio
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Query
from app.database import save_listings, get_listing_by_id_db
from app.services.geolocation import address_to_coords
from app.routes._shared import CITY_CENTERS, TYPES_QUERY_DESC, cached_listings, listing_query_cache, listing_cache_ttl, listing_cache_time
from src.classes import NLocation
from src.util import get_article_listings, get_complex_listings

import app.routes._shared as _shared

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/listings/search",
    summary="지역 기반 매물 검색",
    description=(
        "지역명(동·역·학교 등)을 입력하면 해당 위치 주변 매물 목록을 반환합니다.\n\n"
        "동일한 query는 60초 동안 캐시됩니다. types 필터를 사용하면 캐시가 적용되지 않습니다."
    ),
    response_description="매물 리스트",
)
async def search_listings(
    query: str = Query(..., description="지역명 또는 주소. 예) 강남구, 홍대입구역"),
    types: Optional[List[str]] = Query(None, description=TYPES_QUERY_DESC),
):
    start = time.perf_counter()

    if (
        not types
        and _shared.listing_query_cache["query"] == query
        and _shared.listing_cache_time is not None
        and (time.time() - _shared.listing_cache_time) < _shared.listing_cache_ttl
    ):
        logger.info(f"[리스트 캐시 반환] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": _shared.listing_query_cache["listings"]}

    try:
        lat, lng = await address_to_coords(query)
        loc = NLocation(lat, lng)
        listings = []

        await asyncio.sleep(0.3)
        results = await asyncio.gather(
            get_article_listings(loc, pages=2, estate_types=types),
            get_complex_listings(loc, estate_types=types),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"[매물 조회 실패] {r}")
            else:
                listings.extend(r)

        saved = await asyncio.to_thread(save_listings, listings, query)

        if not types:
            _shared.cached_listings = saved
            _shared.listing_query_cache["query"] = query
            _shared.listing_query_cache["listings"] = saved
            _shared.listing_cache_time = time.time()

        logger.info(f"[리스트 검색 완료] {len(saved)}건, {time.perf_counter() - start:.2f}초 소요")
        return {"listings": saved}

    except Exception as e:
        logger.error(f"[지역 검색 오류] {e}")
        return {"error": str(e)}


@router.get(
    "/listings/all",
    summary="전국 주요 도시 매물 조회",
    description=(
        "서울·부산·대구 등 13개 주요 도시 중심 좌표 기준으로 매물을 가져옵니다.\n\n"
        "13개 도시를 동시에 조회하므로 응답에 수십 초가 걸릴 수 있습니다."
    ),
    response_description="도시별 매물 딕셔너리",
)
async def nationwide_listings(
    types: Optional[List[str]] = Query(None, description=TYPES_QUERY_DESC),
):
    results = {}
    all_listings = []

    async def fetch(city: str, lat: float, lng: float):
        loc = NLocation(lat, lng)
        city_results = await asyncio.gather(
            get_article_listings(loc, pages=2, estate_types=types),
            get_complex_listings(loc, estate_types=types),
            return_exceptions=True,
        )
        await asyncio.sleep(0.5)
        combined = []
        for r in city_results:
            if isinstance(r, Exception):
                logger.warning(f"[{city}] 조회 실패: {r}")
            else:
                combined.extend(r)
        return combined

    tasks = [fetch(city, lat, lng) for city, (lat, lng) in CITY_CENTERS.items()]
    listings_per_city = await asyncio.gather(*tasks)

    for (city, _), city_listings in zip(CITY_CENTERS.items(), listings_per_city):
        saved = await asyncio.to_thread(save_listings, city_listings, city)
        results[city] = saved
        all_listings.extend(saved)

    _shared.cached_listings = all_listings
    return results


@router.get(
    "/listings/{id}",
    summary="ID로 개별 매물 조회",
    description=(
        "listings/search 또는 listings/all에서 반환된 id로 개별 매물 상세 정보를 조회합니다.\n\n"
        "존재하지 않는 ID를 요청하면 error 메시지를 반환합니다."
    ),
    response_description="단일 매물 상세 정보",
)
def get_listing_by_id(id: int):
    row = get_listing_by_id_db(id)
    if row:
        return row
    return {"error": f"해당 ID({id})의 매물이 존재하지 않습니다."}
