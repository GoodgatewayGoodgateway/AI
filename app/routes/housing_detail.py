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
from src.util import get_article_listings

from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ===== 캐시 =====
address_cache = {}
type_cache = {}
listing_query_cache = {"query": None, "listings": []}
listing_cache_ttl = 60  # 캐시 유효 시간 (초)
listing_cache_time = None

async def cached_coords_to_address(lat, lng):
    key = f"{lat:.5f},{lng:.5f}"
    if key in address_cache:
        return address_cache[key]
    address = await coords_to_address(lat, lng)
    address_cache[key] = address
    return address

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
@router.post(
    "/comparison",
    summary="유사 매물 비교 API",
    description="주소 및 유형을 기반으로 유사 매물 평균 가격과 비교합니다.",
    response_description="비교 분석 결과 및 유사 매물 리스트"
)
async def compare_only(data: HousingRequest = Body(...)):
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)

        inferred_type_name = data.type or await infer_type_from_address(data.address)
        type_label_to_code = {
            "아파트": "APT", "APT": "APT",
            "오피스텔": "OPST", "OPST": "OPST",
            "원룸": "OR", "OR": "OR",
            "빌라": "VL", "VL": "VL",
            "다가구": "DDDGG", "DDDGG": "DDDGG",
            "주택": "HOJT", "HOJT": "HOJT",
            "연립주택": "JWJT", "JWJT": "JWJT"
        }
        inferred_type_code = type_label_to_code.get(inferred_type_name, "APT")

        cmp_result = await compare_with_similars(
            area=area_m2,
            deposit=data.deposit,
            monthly=data.monthly,
            lat=lat,
            lng=lng,
            target_type=inferred_type_code
        )
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result

        return {
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area)
            },
            "similar_listings": [
                {
                    "address": s.address,
                    "area": s.area,
                    "deposit": s.deposit,
                    "monthly": s.monthly,
                    "price": s.price,
                    "lat": s.lat,
                    "lng": s.lng,
                    "distance_km": s.distance_km
                }
                for s in cmp.similar_listings
            ]
        }

    except Exception as e:
        logger.error(f"[유사 매물 비교 실패] {e}")
        return {"error": str(e)}

@router.post(
    "/summary",
    summary="AI 요약 문장 생성",
    description="입력한 매물 정보로 AI가 요약 문장을 생성합니다.",
    response_description="요약 + 매물 분석 + 유사 매물"
)
async def get_ai_summary(data: HousingRequest = Body(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)

        # 🔁 매물 유형 처리
        inferred_type_name = data.type or await infer_type_from_address(data.address)

        type_label_to_code = {
            "아파트": "APT", "APT": "APT",
            "오피스텔": "OPST", "OPST": "OPST",
            "원룸": "OR", "OR": "OR",
            "빌라": "VL", "VL": "VL",
            "다가구": "DDDGG", "DDDGG": "DDDGG",
            "주택": "HOJT", "HOJT": "HOJT",
            "연립주택": "JWJT", "JWJT": "JWJT"
        }
        inferred_type_code = type_label_to_code.get(inferred_type_name, "APT")

        # 🔎 디버깅 로그
        logger.info(f"[타입 확인] name={inferred_type_name}, code={inferred_type_code}")

        # 주변 편의시설 비동기 태스크
        fac_task = asyncio.create_task(async_get_nearby_facilities(lat, lng))

        if inferred_type_code == "OR":
            logger.info("[분기 확인] OR 타입 분기 진입 ✅")
            cmp_result = await compare_with_similars(
                area=area_m2,
                deposit=data.deposit,
                monthly=data.monthly,
                lat=lat,
                lng=lng,
                target_type="OR"
            )
            fac_dict = await fac_task
        else:
            logger.info("[분기 확인] OR 아님 → sector API 실행 ❌")
            cmp_task = compare_with_similars(
                area=area_m2,
                deposit=data.deposit,
                monthly=data.monthly,
                lat=lat,
                lng=lng,
                target_type=inferred_type_code
            )
            fac_dict, cmp_result = await asyncio.gather(fac_task, cmp_task)

        fac = FacilitySummary(**fac_dict)
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result
        summary = generate_summary(data, fac, cmp)

        logger.info(f"[요약 생성 완료] {time.perf_counter() - start:.2f}초 소요")

        return {
            "listing": {
                "name": "사용자 입력 매물",
                "type": inferred_type_name,
                "address": data.address,
                "deposit": data.deposit,
                "monthly": data.monthly,
                "price": data.deposit + data.monthly * 10,
                "area_pyeong": round(data.netLeasableArea, 1),
                "area_m2": round(area_m2, 1),
                "lat": lat,
                "lng": lng,
                "source": "input"
            },
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area)
            },
            "summary": summary,
            "similar_listings": [
                {
                    "name": s.address,
                    "address": s.address,
                    "deposit": s.deposit,
                    "monthly": s.monthly,
                    "price": s.price,
                    "area": s.area,
                    "lat": s.lat,
                    "lng": s.lng,
                    "type": inferred_type_name,
                    "distance_km": s.distance_km
                }
                for s in cmp.similar_listings
            ]
        }

    except Exception as e:
        logger.error(f"[요약 생성 실패] {e} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}


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

@router.get(
    "/listings/search",
    summary="지역 기반 매물 검색",
    description="지역명(동, 역, 학교 등)을 입력하면 해당 위치 주변의 매물 리스트를 반환합니다.",
    response_description="매물 리스트"
)
async def search_listings(query: str = Query(...)):
    global cached_listings, listing_cache_time

    start = time.perf_counter()

    # 캐시 확인
    if (
        listing_query_cache["query"] == query
        and listing_cache_time is not None
        and (time.time() - listing_cache_time) < listing_cache_ttl
    ):
        logger.info(f"[리스트 캐시 반환 완료] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": listing_query_cache["listings"]}

    try:
        lat, lng = await address_to_coords(query)
        loc = NLocation(lat, lng)
        listings = []

        # article 매물 조회
        try:
            await asyncio.sleep(0.3)  # rate-limit 완화
            article_list = await get_article_listings(loc)
            listings.extend(article_list)
        except Exception as e:
            logger.warning(f"[articleList 조회 실패] {e}")

        # 캐싱
        cached_listings = [{"id": i, **l} for i, l in enumerate(listings)]
        listing_query_cache["query"] = query
        listing_query_cache["listings"] = cached_listings
        listing_cache_time = time.time()

        logger.info(f"[리스트 검색 완료] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": cached_listings}

    except Exception as e:
        logger.error(f"[지역 검색 오류] {str(e)} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}

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

@router.get(
    "/listings/all",
    summary="전국 주요 도시 매물 조회",
    description="서울, 부산, 대구 등 주요 도시 중심 좌표 기준으로 매물을 가져옵니다.",
    response_description="도시별 매물 리스트"
)
async def nationwide_listings():
    global cached_listings
    results = {}
    all_listings = []
    idx = 0

    async def fetch(city: str, lat: float, lng: float):
        try:
            # ✅ 네이버 매물만 조회 (카카오 주소 변환 없음)
            listings = await get_article_listings(NLocation(lat, lng))
            await asyncio.sleep(0.5)  # 네이버 API rate limit 완화
            return listings
        except Exception as e:
            logger.warning(f"[{city}] 조회 실패: {e}")
            return []

    tasks = [fetch(city, lat, lng) for city, (lat, lng) in CITY_CENTERS.items()]
    listings_per_city = await asyncio.gather(*tasks)

    for (city, _), listings in zip(CITY_CENTERS.items(), listings_per_city):
        city_results = []
        for l in listings:
            wrapped = {"id": idx, **l}  # 개별 매물에 id 부여
            city_results.append(wrapped)
            all_listings.append(wrapped)
            idx += 1
        results[city] = city_results

    # ✅ 전국 매물 캐시에 저장 (상세 조회용)
    cached_listings = all_listings
    return results


@router.get(
    "/listings/{id}",
    summary="ID로 개별 매물 조회",
    description="리스트에서 얻은 ID로 개별 매물 상세를 조회합니다.",
    response_description="단일 매물 정보"
)
def get_listing_by_id(id: int):
    if not cached_listings:
        return {"error": "검색된 매물이 없습니다. 먼저 /api/listings/search 또는 /api/listings/nationwide를 실행하세요."}
    if 0 <= id < len(cached_listings):
        return cached_listings[id]
    return {"error": f"해당 ID({id})의 매물이 존재하지 않습니다."}