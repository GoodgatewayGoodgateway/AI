import logging
import json, math, asyncio, requests, time
from fastapi import APIRouter, Body, Query
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from app.services.geolocation import address_to_coords, coords_to_address
from app.services.facilities import async_get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary
from src.classes import NLocation
from src.util import get_article_listings
from typing import Dict, Any

# ===== 기본 설정 =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter()

# ===== 전역 캐시 =====
cached_listings: list[dict[str, Any]] = []
address_cache: Dict[str, str] = {}
type_cache: Dict[str, str] = {}
listing_query_cache = {"query": None, "listings": []} 
listing_cache_ttl = 60  # 초 단위
listing_cache_time: float | None = None

# ===== 상수 =====
TYPE_MAP = {
    "아파트": "APT", "APT": "APT",
    "오피스텔": "OPST", "OPST": "OPST",
    "원룸": "OR", "OR": "OR",
    "빌라": "VL", "VL": "VL",
    "다가구": "DDDGG", "DDDGG": "DDDGG",
    "주택": "HOJT", "HOJT": "HOJT",
    "연립주택": "JWJT", "JWJT": "JWJT"
}

CITY_CENTERS = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "대전": (36.3504, 127.3845),
    "광주": (35.1595, 126.8526),
    "인천": (37.4563, 126.7052),
    "제주": (33.4996, 126.5312),
    "수원": (37.2635, 127.0286),
    "울산": (35.5384, 129.3114),
    "창원": (35.2285, 128.6865),
    "청주": (36.6359, 127.4914),
    "천안": (36.8149, 127.1192),
    "전주": (35.8200, 127.1523),
}

# ===== 유틸 =====
def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

# ===== 캐시 =====
async def cached_coords_to_address(lat: float, lng: float) -> str:
    key = f"{lat:.5f},{lng:.5f}"
    if key not in address_cache:
        address_cache[key] = await coords_to_address(lat, lng)
    return address_cache[key]

async def infer_type_from_address(address: str) -> str:
    if address in type_cache:
        return type_cache[address]

    lat, lng = await address_to_coords(address)
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    params = {
        "rletTpCd": "VL:DDDGG:HOJT:JWJT:OR:APT:OPST",
        "tradTpCd": "A1:B1:B2",
        "z": 16, "lat": lat, "lon": lng,
        "btm": lat - 0.002, "lft": lng - 0.002,
        "top": lat + 0.002, "rgt": lng + 0.002,
        "page": 1
    }
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json()
        inferred = data["body"][0].get("rletTpNm", "기타") if data.get("body") else "기타"
        type_cache[address] = inferred
        return inferred
    except Exception as e:
        logger.warning(f"[유형 추론 실패] {e}")
        return "기타"

# ===== 유사 매물 비교 =====
@router.post("/comparison", summary="유사 매물 비교 API")
async def compare_only(data: HousingRequest = Body(...)):
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        inferred_type = data.type or await infer_type_from_address(data.address)
        code = TYPE_MAP.get(inferred_type, "APT")

        cmp_result = await compare_with_similars(
            area=area_m2, deposit=data.deposit, monthly=data.monthly,
            lat=lat, lng=lng, target_type=code
        )
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result

        return {
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area)
            },
            "similar_listings": [s.__dict__ for s in cmp.similar_listings]
        }
    except Exception as e:
        logger.error(f"[유사 매물 비교 실패] {e}")
        return {"error": str(e)}

# ===== AI 요약 생성 =====
@router.post("/summary", summary="AI 요약 문장 생성")
async def get_ai_summary(data: HousingRequest = Body(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        inferred_type = data.type or await infer_type_from_address(data.address)
        code = TYPE_MAP.get(inferred_type, "APT")

        logger.info(f"[타입 확인] name={inferred_type}, code={code}")

        fac_task = asyncio.create_task(async_get_nearby_facilities(lat, lng))
        cmp_task = asyncio.create_task(compare_with_similars(
            area=area_m2, deposit=data.deposit, monthly=data.monthly,
            lat=lat, lng=lng, target_type=code
        ))

        fac_dict, cmp_result = await asyncio.gather(fac_task, cmp_task)

        fac = FacilitySummary(**fac_dict)
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result
        summary = generate_summary(data, fac, cmp)

        logger.info(f"[요약 생성 완료] {time.perf_counter() - start:.2f}초 소요")

        return {
            "listing": {
                "address": data.address,
                "type": inferred_type,
                "deposit": data.deposit,
                "monthly": data.monthly,
                "price": data.deposit + data.monthly * 10,
                "area_pyeong": data.netLeasableArea,
                "area_m2": area_m2,
                "lat": lat, "lng": lng
            },
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area)
            },
            "summary": summary,
            "similar_listings": [s.__dict__ for s in cmp.similar_listings]
        }

    except Exception as e:
        logger.error(f"[요약 생성 실패] {e} ({time.perf_counter() - start:.2f}초)")
        return {"error": str(e)}

# ===== 주변 편의시설 =====
@router.get("/facilities", summary="주변 편의시설 조회")
async def get_facilities(query: str = Query(...)):
    try:
        lat, lng = await address_to_coords(query)
        fac = await async_get_nearby_facilities(lat, lng)
        return fac
    except Exception as e:
        logger.error(f"[편의시설 조회 실패] {e}")
        return {"error": str(e)}

# ===== 지역 기반 매물 검색 =====
@router.get("/listings/search", summary="지역 기반 매물 검색")
async def search_listings(query: str = Query(...)):
    global cached_listings, listing_cache_time
    start = time.perf_counter()

    if (
        listing_query_cache["query"] == query
        and listing_cache_time
        and (time.time() - listing_cache_time) < listing_cache_ttl
    ):
        logger.info(f"[리스트 캐시 반환 완료] {time.perf_counter() - start:.2f}초")
        return {"listings": listing_query_cache["listings"]}

    try:
        lat, lng = await address_to_coords(query)
        await asyncio.sleep(0.3)
        listings = await get_article_listings(NLocation(lat, lng))
        cached_listings = [{"id": i, **l} for i, l in enumerate(listings)]

        listing_query_cache.update({"query": query, "listings": cached_listings})
        listing_cache_time = time.time()

        logger.info(f"[리스트 검색 완료] {time.perf_counter() - start:.2f}초")
        return {"listings": cached_listings}
    except Exception as e:
        logger.error(f"[지역 검색 오류] {e}")
        return {"error": str(e)}

# ===== 전국 주요 도시 매물 =====
@router.get("/listings/all", summary="전국 주요 도시 매물 조회")
async def nationwide_listings():
    global cached_listings
    results, all_listings, idx = {}, [], 0

    async def fetch(city: str, lat: float, lng: float):
        try:
            await asyncio.sleep(0.5)
            return await get_article_listings(NLocation(lat, lng))
        except Exception as e:
            logger.warning(f"[{city}] 조회 실패: {e}")
            return []

    listings_per_city = await asyncio.gather(*[fetch(c, *loc) for c, loc in CITY_CENTERS.items()])

    for (city, _), city_list in zip(CITY_CENTERS.items(), listings_per_city):
        city_data = [{"id": idx + i, **l} for i, l in enumerate(city_list)]
        results[city] = city_data
        all_listings.extend(city_data)
        idx += len(city_list)

    cached_listings = all_listings
    return results

# ===== ID 기반 단일 매물 =====
@router.get("/listings/{id}", summary="ID로 개별 매물 조회")
def get_listing_by_id(id: int):
    if not cached_listings:
        return {"error": "검색된 매물이 없습니다. 먼저 /listings/search 또는 /listings/all 호출 필요"}
    if 0 <= id < len(cached_listings):
        return cached_listings[id]
    return {"error": f"해당 ID({id})의 매물이 존재하지 않습니다."}
