import logging
import re, json, math, asyncio, requests, time
from fastapi import APIRouter, Body, Query
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from app.services.geolocation import address_to_coords, coords_to_address
from app.services.facilities import async_get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary
from src.classes import NAddon, NLocation
from src.util import async_get_parallel_things, get_sector, get_things, distance_between
from typing import List
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ===== 캐시 =====
address_cache = {}
type_cache = {}
listing_query_cache = {"query": None, "listings": []}

async def cached_coords_to_address(lat, lng):
    key = f"{round(lat, 5)},{round(lng, 5)}"
    if key in address_cache:
        return address_cache[key]
    addr = await coords_to_address(lat, lng)
    address_cache[key] = addr
    return addr

async def infer_type_from_address(address: str) -> str:
    if address in type_cache:
        return type_cache[address]

    lat, lng = await address_to_coords(address)
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    params = {
        "rletTpCd": "VL:DDDGG:HOJT:JWJT:OR:APT:OPST",
        "tradTpCd": "A1:B1:B2",
        "z": 16,
        "lat": lat,
        "lon": lng,
        "btm": lat - 0.002,
        "lft": lng - 0.002,
        "top": lat + 0.002,
        "rgt": lng + 0.002,
        "page": 1
    }

    res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
    data = res.json()
    if data["body"]:
        inferred = data["body"][0].get("rletTpNm", "기타")
        type_cache[address] = inferred
        return inferred
    return "기타"

# ===== 유틸 =====
def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

# ===== 라우터 =====
@router.get(
    "/facilities",
    summary="주변 편의시설 조회",
    description="주소 또는 좌표를 기반으로 주변 카페, 편의점, 헬스장을 조회합니다.",
    response_description="FacilitySummary 객체 반환"
)
async def get_facilities(query: str = Query(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(query)
        fac_dict = await async_get_nearby_facilities(lat, lng)
        logger.info(f"[편의시설 조회 완료] {time.perf_counter() - start:.2f}초 소요")
        return fac_dict
    except Exception as e:
        logger.error(f"[편의시설 조회 실패] {e} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}

@router.post(
    "/summary",
    summary="AI 요약 문장 생성",
    description="입력한 매물 정보로 AI가 요약 문장을 생성합니다.",
    response_description="요약 문장"
)
async def get_ai_summary(data: HousingRequest = Body(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)

        inferred_type = await infer_type_from_address(data.address)
        fac_dict = await async_get_nearby_facilities(lat, lng)
        fac = FacilitySummary(**fac_dict)

        cmp_result = compare_with_similars(
            area=area_m2,
            deposit=data.deposit,
            monthly=data.monthly,
            lat=lat,
            lng=lng
        )
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result

        summary = generate_summary(data, fac, cmp)

        logger.info(f"[요약 생성 완료] {time.perf_counter() - start:.2f}초 소요")
        return {
            "name": "사용자 입력 매물",
            "address": data.address,
            "area": round(area_m2, 1),
            "deposit": data.deposit,
            "monthly": data.monthly,
            "price": data.deposit + data.monthly * 10,
            "lat": lat,
            "lng": lng,
            "type": inferred_type,
            "distance_km": 0.0,
            "source": "input",
            "summary": summary
        }
    except Exception as e:
        logger.error(f"[요약 생성 실패] {e} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}

@router.get(
    "/listings/search",
    summary="지역 기반 매물 검색",
    description="지역명(동, 역, 학교 등)을 입력하면 해당 위치 주변의 매물 리스트를 반환합니다.",
    response_description="매물 리스트"
)
async def search_listings(query: str = Query(...)):
    global cached_listings
    start = time.perf_counter()
    if listing_query_cache["query"] == query:
        logger.info(f"[리스트 캐시 반환 완료] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": listing_query_cache["listings"]}

    try:
        lat, lng = await address_to_coords(query)
        loc = NLocation(lat, lng)
        listings = []

        # 복합 단지 매물 (APT, OPST 등)
        try:
            sector = get_sector(loc)
            complex_things = await async_get_parallel_things(sector)
            for t in complex_things:
                if t.lease.mn is None or t.area.representative is None:
                    continue
                address_name = await cached_coords_to_address(t.loc.lat, t.loc.lon)
                TYPE_LABELS = {
                    "APT": "아파트", "OPST": "오피스텔", "VL": "빌라",
                    "DDDGG": "다가구", "HOJT": "주택", "JWJT": "연립주택", "OR": "원룸",
                }
                listings.append({
                    "name": t.name,
                    "address": address_name,
                    "area": round(t.area.representative * 3.3, 1),
                    "deposit": t.lease.mn,
                    "monthly": 0,
                    "price": t.lease.mn,
                    "lat": t.loc.lat,
                    "lng": t.loc.lon,
                    "type": TYPE_LABELS.get(t.type, "기타"),
                    "distance_km": round(distance_between(loc, t.loc) / 1000, 2),
                    "source": "complex"
                })
        except Exception as e:
            logger.warning(f"[complex 크롤링 실패] {e}")

        # 일반 article 매물 (빌라/단독/원룸 등) 분리된 함수로 처리
        try:
            from src.util import get_article_listings
            article_list = await get_article_listings(loc)
            listings.extend(article_list)
        except Exception as e:
            logger.warning(f"[articleList 조회 실패] {e}")

        cached_listings = [{"id": i, **l} for i, l in enumerate(listings)]
        listing_query_cache["query"] = query
        listing_query_cache["listings"] = cached_listings
        logger.info(f"[리스트 검색 완료] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": cached_listings}

    except Exception as e:
        logger.error(f"[지역 검색 오류] {str(e)} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}

@router.get(
    "/listings/{id}",
    summary="ID로 개별 매물 조회",
    description="리스트에서 얻은 ID로 개별 매물 상세를 조회합니다.",
    response_description="단일 매물 정보"
)
def get_listing_by_id(id: int):
    if 0 <= id < len(cached_listings):
        return cached_listings[id]
    return {"error": f"해당 ID({id})의 매물이 존재하지 않습니다."}
