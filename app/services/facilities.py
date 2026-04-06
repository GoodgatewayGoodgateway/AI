import os
import time
import asyncio
import httpx
from dotenv import load_dotenv
from app.schemas import FacilityItem, FacilitySummary

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

# 카카오 장소 카테고리 코드 정의
CATEGORIES = {
    "cafes": "CE7",                 # 카페
    "convenience_stores": "CS2",   # 편의점
    "gyms": "CT1",                  # 헬스장/문화시설
    "subway_stations": "SW8",      # 지하철역
    "schools": "SC4",              # 학교
    "hospitals": "HP8",            # 병원
    "banks": "BK9",                # 은행
    "parks": "PK6",                # 공원
}

# 편의시설 TTL 캐시: { "lat,lng" -> (result_dict, timestamp) }
_FACILITIES_CACHE: dict[str, tuple[dict, float]] = {}
_FACILITIES_TTL = 300  # 5분

# 카테고리별 비동기 요청
async def fetch_category(client: httpx.AsyncClient, lat: float, lng: float, category_code: str) -> list[FacilityItem]:
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "category_group_code": category_code,
        "x": lng,
        "y": lat,
        "radius": 1500,
        "size": 15
    }
    try:
        resp = await client.get(CATEGORY_URL, headers=headers, params=params, timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
        return [
            FacilityItem(
                name=doc.get("place_name"),
                lat=float(doc.get("y")),
                lng=float(doc.get("x"))
            )
            for doc in data.get("documents", [])
        ]
    except Exception as e:
        print(f"[카테고리 요청 실패] {category_code}: {e}")
        return []

# 비동기 편의시설 전체 수집 (TTL 캐시 적용)
async def async_get_nearby_facilities(lat: float, lng: float) -> dict:
    cache_key = f"{lat:.4f},{lng:.4f}"
    cached = _FACILITIES_CACHE.get(cache_key)
    if cached is not None:
        result, ts = cached
        if time.time() - ts < _FACILITIES_TTL:
            return result

    async with httpx.AsyncClient() as client:
        tasks = {
            name: fetch_category(client, lat, lng, code)
            for name, code in CATEGORIES.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)
    result = dict(zip(tasks.keys(), results))
    _FACILITIES_CACHE[cache_key] = (result, time.time())
    return result
