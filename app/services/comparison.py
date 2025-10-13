import asyncio
import httpx
from app.schemas import ComparisonResult, SimilarListing
from src.classes import NLocation
from src.util import (
    get_sector,
    async_get_parallel_things,
    distance_between,
    get_article_listings
)

# 🔹 캐시 추가 (같은 지역 재사용)
_sector_cache = {}

async def safe_get_sector(location: NLocation, retries: int = 3):
    """429 Rate Limit 방지용 안전 섹터 요청"""
    key = f"{round(location.lat, 4)}_{round(location.lon, 4)}"
    if key in _sector_cache:
        return _sector_cache[key]

    url = (
        f"https://new.land.naver.com/api/cortars"
        f"?centerLat={location.lat}&centerLon={location.lon}&zoom=16"
    )
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(retries):
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=headers)

        if res.status_code == 200:
            data = res.json()
            _sector_cache[key] = data
            return data
        elif res.status_code == 429:
            wait = 2 * (attempt + 1)
            print(f"[RATE LIMIT] 네이버 429 → {wait}초 대기 후 재시도 ({attempt+1}/{retries})")
            await asyncio.sleep(wait)
        else:
            raise RuntimeError(f"섹터 요청 실패: {res.status_code} {res.text[:100]}")

    raise RuntimeError("섹터 정보를 불러오지 못했습니다: Rate limit 지속됨")


async def compare_with_similars(area: float, deposit: int, monthly: int, lat: float, lng: float, target_type: str) -> ComparisonResult:
    current_price = deposit + (monthly * 10)
    current_loc = NLocation(lat, lng)

    # ✅ OR 타입은 섹터 조회 스킵
    sector = None
    if target_type != "OR":
        try:
            # 기존 get_sector 대신 safe_get_sector 사용
            sector = await safe_get_sector(current_loc)
        except Exception as e:
            raise RuntimeError(f"섹터 정보를 불러오지 못했습니다: {e}")

    # ✅ 매물 조회
    if target_type == "OR":  # 원룸일 경우 article API 사용
        things = await get_article_listings(current_loc)
        valid_listings = [
            SimilarListing(
                address=t["address"],
                area=t["area"],
                deposit=t["deposit"],
                monthly=t["monthly"],
                price=t["price"],
                lat=t["lat"],
                lng=t["lng"],
                distance_km=t["distance_km"]
            )
            for t in things if t.get("area") and t.get("deposit") is not None
        ]
    else:  # 나머지 유형 → complex 단지
        try:
            complex_things = await async_get_parallel_things(sector)
        except Exception as e:
            raise RuntimeError(f"복합 단지 매물을 불러오지 못했습니다: {e}")

        valid_listings = []
        for t in complex_things:
            if not t.lease.mn or not t.area.representative:
                continue
            if t.type != target_type:
                continue

            area_m2 = round(t.area.representative * 3.3, 1)
            distance_km = round(distance_between(current_loc, t.loc) / 1000, 2)
            valid_listings.append(SimilarListing(
                address=t.name,
                area=area_m2,
                deposit=t.lease.mn,
                monthly=0,
                price=t.lease.mn,
                lat=t.loc.lat,
                lng=t.loc.lon,
                distance_km=distance_km
            ))

    if not valid_listings:
        raise ValueError("해당 유형의 유사 매물을 찾을 수 없습니다.")

    # ✅ 평균 계산
    total_price = sum(t.price for t in valid_listings)
    total_area = sum(t.area for t in valid_listings)
    count = len(valid_listings)

    avg_price = round(total_price / count)
    avg_area = round(total_area / count, 1)
    cheaper = current_price < avg_price

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=valid_listings
    )
