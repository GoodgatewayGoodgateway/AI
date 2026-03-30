import logging
import asyncio, requests, time
from fastapi import APIRouter, Body, Query
from typing import List, Optional
from app.schemas import (
    HousingRequest, FacilitySummary, ComparisonResult,
    RecommendRequest, FavoriteRequest,
)
from app.services.geolocation import address_to_coords, coords_to_address
from app.services.facilities import async_get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary
from app.services.score import calculate_score
from app.database import (
    save_listings, get_listing_by_id_db,
    add_favorite, get_favorites_db, delete_favorite,
    get_market_trend_db,
)
from src.classes import NLocation
from src.util import get_article_listings, get_complex_listings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ──────────────────────────────────────────────
# 캐시
# ──────────────────────────────────────────────
address_cache: dict = {}
type_cache: dict = {}
listing_query_cache: dict = {"query": None, "listings": []}
listing_cache_ttl: int = 60
listing_cache_time: Optional[float] = None
cached_listings: list = []

# ──────────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────────
def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

TYPE_LABEL_TO_CODE = {
    "아파트": "APT", "APT": "APT", "A01": "APT",
    "오피스텔": "OPST", "OPST": "OPST", "A02": "OPST",
    "원룸": "OR", "OR": "OR", "C01": "OR",
    "빌라": "VL", "VL": "VL", "다세대주택": "VL",
    "다가구": "DDDGG", "DDDGG": "DDDGG", "다가구주택": "DDDGG",
    "주택": "HOJT", "HOJT": "HOJT", "단독주택": "HOJT",
    "연립주택": "JWJT", "JWJT": "JWJT",
}

async def infer_type_from_address(address: str) -> str:
    if address in type_cache:
        return type_cache[address]
    lat, lng = await address_to_coords(address)
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    params = {
        "rletTpCd": "APT:OPST:VL:DDDGG:HOJT:JWJT:OR",
        "tradTpCd": "A1:B1:B2",
        "z": 16, "lat": lat, "lon": lng,
        "btm": lat - 0.002, "lft": lng - 0.002,
        "top": lat + 0.002, "rgt": lng + 0.002,
        "page": 1,
    }
    try:
        res = requests.get(
            url, params=params,
            headers={"User-Agent": "Mozilla/5.0"}, timeout=5
        )
        data = res.json()
        if data.get("body"):
            inferred = data["body"][0].get("rletTpNm", "기타")
            type_cache[address] = inferred
            return inferred
    except Exception:
        pass
    return "기타"

_TYPES_QUERY_DESC = (
    "매물 유형 필터 (선택, 반복 입력 가능).\n"
    "입력하지 않으면 전체 유형을 반환합니다.\n\n"
    "사용 가능한 값:\n"
    "- 원룸 (또는 OR)\n"
    "- 빌라 (또는 VL)\n"
    "- 오피스텔 (또는 OPST)\n"
    "- 아파트 (또는 APT)\n"
    "- 다가구 (또는 DDDGG)\n"
    "- 주택 (또는 HOJT)\n"
    "- 연립주택 (또는 JWJT)"
)


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post(
    "/comparison",
    summary="유사 매물 비교",
    description=(
        "입력한 매물을 주변 유사 매물들과 가격·면적 기준으로 비교합니다.\n\n"
        "Request Body:\n\n"
        "- address (필수): 매물 주소. 도로명·지번 모두 가능합니다. 예) 서울시 마포구 합정동\n"
        "- netLeasableArea (필수): 전용면적 (평 단위). 예) 18.5\n"
        "- deposit (필수): 보증금 (만원 단위). 예) 1000 → 1,000만원\n"
        "- monthly (필수): 월세 (만원 단위). 매매·전세의 경우 0을 입력합니다.\n"
        "- type (선택): 매물 유형. 입력하지 않으면 주소 기반으로 자동 추론합니다.\n\n"
        "Response:\n\n"
        "- analysis.cheaper_than_average: 입력 매물이 평균보다 저렴한지 여부\n"
        "- analysis.average_price: 유사 매물 평균 환산가격 (만원)\n"
        "- analysis.average_area_m2: 유사 매물 평균 면적 (㎡)\n"
        "- similar_listings: 비교에 사용된 유사 매물 목록\n\n"
        "가격 환산 공식: 환산가격 = 보증금 + 월세 × 10"
    ),
    response_description="유사 매물 비교 분석 결과",
)
async def compare_only(data: HousingRequest = Body(...)):
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        inferred_type_name = data.type or await infer_type_from_address(data.address)
        inferred_type_code = TYPE_LABEL_TO_CODE.get(inferred_type_name, "APT")

        cmp_result = await compare_with_similars(
            area=area_m2, deposit=data.deposit, monthly=data.monthly,
            lat=lat, lng=lng, target_type=inferred_type_code,
        )
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result

        return {
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area),
            },
            "similar_listings": [
                {
                    "address": s.address, "area": s.area,
                    "deposit": s.deposit, "monthly": s.monthly,
                    "price": s.price, "lat": s.lat, "lng": s.lng,
                    "distance_km": s.distance_km,
                }
                for s in cmp.similar_listings
            ],
        }
    except Exception as e:
        logger.error(f"[유사 매물 비교 실패] {e}")
        return {"error": str(e)}


@router.post(
    "/summary",
    summary="AI 요약 문장 생성",
    description=(
        "매물 정보를 입력받아 주변 편의시설·유사 매물 비교 결과를 바탕으로 AI 요약 문장을 생성합니다.\n\n"
        "Request Body:\n\n"
        "- address (필수): 매물 주소. 예) 서울시 마포구 합정동\n"
        "- netLeasableArea (필수): 전용면적 (평 단위). 예) 18.5\n"
        "- deposit (필수): 보증금 (만원 단위). 예) 1000 → 1,000만원\n"
        "- monthly (필수): 월세 (만원 단위). 매매·전세의 경우 0을 입력합니다.\n"
        "- type (선택): 매물 유형. 입력하지 않으면 주소 기반으로 자동 추론합니다.\n\n"
        "Response:\n\n"
        "- listing: 입력 매물 정보 (주소, 가격, 면적, 좌표 포함)\n"
        "- analysis: 유사 매물 비교 결과 (평균 가격·면적, 저렴 여부)\n"
        "- summary: AI가 생성한 요약 문장\n"
        "- similar_listings: 비교에 사용된 유사 매물 목록\n\n"
        "내부 처리 순서: 주소→좌표 변환 → 편의시설 조회 → 유사 매물 비교 → AI 요약 생성"
    ),
    response_description="AI 요약 문장 및 매물 분석 결과",
)
async def get_ai_summary(data: HousingRequest = Body(...)):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        inferred_type_name = data.type or await infer_type_from_address(data.address)
        inferred_type_code = TYPE_LABEL_TO_CODE.get(inferred_type_name, "APT")

        logger.info(f"[타입 확인] name={inferred_type_name}, code={inferred_type_code}")

        fac_task = asyncio.create_task(async_get_nearby_facilities(lat, lng))
        cmp_task = compare_with_similars(
            area=area_m2, deposit=data.deposit, monthly=data.monthly,
            lat=lat, lng=lng, target_type=inferred_type_code,
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
                "lat": lat, "lng": lng,
                "source": "input",
            },
            "analysis": {
                "cheaper_than_average": cmp.cheaper_than_average,
                "average_price": cmp.average_price,
                "average_area_m2": cmp.average_area,
                "average_area_pyeong": to_pyeong(cmp.average_area),
            },
            "summary": summary,
            "similar_listings": [
                {
                    "name": s.address, "address": s.address,
                    "deposit": s.deposit, "monthly": s.monthly,
                    "price": s.price, "area": s.area,
                    "lat": s.lat, "lng": s.lng,
                    "type": inferred_type_name,
                    "distance_km": s.distance_km,
                }
                for s in cmp.similar_listings
            ],
        }
    except Exception as e:
        logger.error(f"[요약 생성 실패] {e} ({time.perf_counter() - start:.2f}초 소요)")
        return {"error": str(e)}


@router.get(
    "/facilities",
    summary="주변 편의시설 조회",
    description=(
        "주소 또는 지역명을 입력하면 반경 1500m 이내 편의시설 8개 카테고리를 반환합니다.\n\n"
        "Query Parameter:\n\n"
        "- query (필수): 주소 또는 지역명. 예) 서울시 마포구 합정동, 홍대입구역\n\n"
        "Response:\n\n"
        "- cafes: 카페 목록\n"
        "- convenience_stores: 편의점 목록\n"
        "- gyms: 헬스장·문화시설 목록\n"
        "- subway_stations: 지하철역 목록\n"
        "- schools: 학교 목록\n"
        "- hospitals: 병원 목록\n"
        "- banks: 은행 목록\n"
        "- parks: 공원 목록\n\n"
        "각 항목은 name, lat, lng 필드를 포함합니다."
    ),
    response_description="8개 카테고리별 편의시설 목록",
)
async def get_facilities(
    query: str = Query(
        ...,
        description="주소 또는 지역명. 예) 서울시 마포구 합정동",
    )
):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(query)
        fac_dict = await async_get_nearby_facilities(lat, lng)
        logger.info(f"[편의시설 조회 완료] {time.perf_counter() - start:.2f}초 소요")
        return fac_dict
    except Exception as e:
        logger.error(f"[편의시설 조회 실패] {e}")
        return {"error": str(e)}


@router.get(
    "/listings/search",
    summary="지역 기반 매물 검색",
    description=(
        "지역명(동·역·학교 등)을 입력하면 해당 위치 주변 매물 목록을 반환합니다.\n\n"
        "Query Parameters:\n\n"
        "- query (필수): 지역명 또는 주소. 예) 강남구, 홍대입구역, 대구 상인동\n"
        "- types (선택, 반복 가능): 매물 유형 필터. 예) ?types=원룸&types=빌라\n\n"
        "사용 가능한 types 값:\n"
        "- 원룸 (또는 OR)\n"
        "- 빌라 (또는 VL)\n"
        "- 오피스텔 (또는 OPST)\n"
        "- 아파트 (또는 APT)\n"
        "- 다가구 (또는 DDDGG)\n"
        "- 주택 (또는 HOJT)\n"
        "- 연립주택 (또는 JWJT)\n\n"
        "Response:\n\n"
        "- listings: 매물 목록. 각 항목은 id, name, address, area(㎡), deposit, monthly, price, lat, lng, type, trade_type, distance_km, source 필드를 포함합니다.\n\n"
        "동일한 query는 60초 동안 캐시됩니다. types 필터를 사용하면 캐시가 적용되지 않습니다."
    ),
    response_description="매물 리스트",
)
async def search_listings(
    query: str = Query(
        ...,
        description="지역명 또는 주소. 예) 강남구, 홍대입구역",
    ),
    types: Optional[List[str]] = Query(
        None,
        description=_TYPES_QUERY_DESC,
    ),
):
    global cached_listings, listing_cache_time
    start = time.perf_counter()

    if (
        not types
        and listing_query_cache["query"] == query
        and listing_cache_time is not None
        and (time.time() - listing_cache_time) < listing_cache_ttl
    ):
        logger.info(f"[리스트 캐시 반환] {time.perf_counter() - start:.2f}초 소요")
        return {"listings": listing_query_cache["listings"]}

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
        logger.info(f"[매물 조회] article={len(results[0]) if not isinstance(results[0], Exception) else 'ERR'}건, complex={len(results[1]) if not isinstance(results[1], Exception) else 'ERR'}건")

        saved = await asyncio.to_thread(save_listings, listings, query)

        if not types:
            cached_listings = saved
            listing_query_cache["query"] = query
            listing_query_cache["listings"] = saved
            listing_cache_time = time.time()

        logger.info(f"[리스트 검색 완료] {len(saved)}건, {time.perf_counter() - start:.2f}초 소요")
        return {"listings": saved}

    except Exception as e:
        logger.error(f"[지역 검색 오류] {e} ({time.perf_counter() - start:.2f}초 소요)")
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
    description=(
        "서울·부산·대구 등 13개 주요 도시 중심 좌표 기준으로 매물을 가져옵니다.\n\n"
        "Query Parameter:\n\n"
        "- types (선택, 반복 가능): 매물 유형 필터. 예) ?types=원룸&types=빌라\n\n"
        "사용 가능한 types 값:\n"
        "- 원룸 (또는 OR)\n"
        "- 빌라 (또는 VL)\n"
        "- 오피스텔 (또는 OPST)\n"
        "- 아파트 (또는 APT)\n"
        "- 다가구 (또는 DDDGG)\n"
        "- 주택 (또는 HOJT)\n"
        "- 연립주택 (또는 JWJT)\n\n"
        "Response:\n\n"
        "- 도시명을 키로 하는 딕셔너리. 예) { '서울': [...], '부산': [...] }\n"
        "- 각 매물 항목은 id, name, address, area, deposit, monthly, price, lat, lng, type, city 필드를 포함합니다.\n\n"
        "조회 대상 도시: 서울, 부산, 대구, 대전, 광주, 인천, 제주, 수원, 울산, 창원, 청주, 천안, 전주\n\n"
        "13개 도시를 동시에 조회하므로 응답에 수십 초가 걸릴 수 있습니다."
    ),
    response_description="도시별 매물 딕셔너리",
)
async def nationwide_listings(
    types: Optional[List[str]] = Query(
        None,
        description=_TYPES_QUERY_DESC,
    ),
):
    global cached_listings
    results = {}
    all_listings = []

    async def fetch(city: str, lat: float, lng: float):
        loc = NLocation(lat, lng)
        results = await asyncio.gather(
            get_article_listings(loc, pages=2, estate_types=types),
            get_complex_listings(loc, estate_types=types),
            return_exceptions=True,
        )
        await asyncio.sleep(0.5)
        combined = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"[{city}] 조회 실패: {r}")
            else:
                combined.extend(r)
        return combined

    tasks = [fetch(city, lat, lng) for city, (lat, lng) in CITY_CENTERS.items()]
    listings_per_city = await asyncio.gather(*tasks)

    for (city, _), listings in zip(CITY_CENTERS.items(), listings_per_city):
        saved = await asyncio.to_thread(save_listings, listings, city)
        results[city] = saved
        all_listings.extend(saved)

    cached_listings = all_listings
    return results


@router.get(
    "/listings/{id}",
    summary="ID로 개별 매물 조회",
    description=(
        "listings/search 또는 listings/all에서 반환된 id로 개별 매물 상세 정보를 조회합니다.\n\n"
        "Path Variable:\n\n"
        "- id (필수): 매물 고유 ID. listings/search 또는 listings/all 응답의 각 항목에서 확인할 수 있습니다.\n\n"
        "Response:\n\n"
        "- id, name, address, area, deposit, monthly, price, lat, lng, type, city, source, created_at 필드를 포함합니다.\n\n"
        "존재하지 않는 ID를 요청하면 error 메시지를 반환합니다."
    ),
    response_description="단일 매물 상세 정보",
)
def get_listing_by_id(id: int):
    row = get_listing_by_id_db(id)
    if row:
        return row
    return {"error": f"해당 ID({id})의 매물이 존재하지 않습니다."}


# ──────────────────────────────────────────────
# 지역 시세 통계
# ──────────────────────────────────────────────

@router.get(
    "/market/stats",
    summary="지역 시세 통계 조회",
    description=(
        "지역명을 입력하면 해당 지역의 매물 수, 타입별 평균 가격·면적, 가격 범위를 반환합니다.\n\n"
        "Query Parameters:\n\n"
        "- query (필수): 지역명 또는 주소. 예) 강남구, 홍대입구역\n"
        "- type (선택): 매물 유형 필터. 예) 원룸, 빌라\n\n"
        "Response:\n\n"
        "- total_count: 전체 매물 수\n"
        "- by_type: 타입별 { count, avg_price(만원), avg_area_m2 }\n"
        "- price_range: { min, max } 환산가격 (만원)"
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


# ──────────────────────────────────────────────
# 매물 종합 점수
# ──────────────────────────────────────────────

@router.post(
    "/score",
    summary="매물 종합 점수 평가",
    description=(
        "매물 정보를 입력하면 가격·편의시설·교통을 종합한 점수(0~100)와 등급을 반환합니다.\n\n"
        "Request Body: HousingRequest (address, netLeasableArea, deposit, monthly, type)\n\n"
        "Response:\n\n"
        "- total_score: 종합 점수 (0~100)\n"
        "- breakdown.price_score: 가격 점수 — 시세 대비 저렴할수록 높음 (가중치 50%)\n"
        "- breakdown.facilities_score: 편의시설 점수 — 반경 1500m 내 시설 수 기반 (가중치 30%)\n"
        "- breakdown.transit_score: 교통 점수 — 반경 1500m 내 지하철역 수 기반 (가중치 20%)\n"
        "- grade: S / A / B / C / D / F"
    ),
    response_description="매물 종합 점수 및 등급",
)
async def score_listing(data: HousingRequest = Body(...)):
    try:
        lat, lng = await address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        inferred_type_name = data.type or await infer_type_from_address(data.address)
        inferred_type_code = TYPE_LABEL_TO_CODE.get(inferred_type_name, "APT")

        result = await calculate_score(
            area_m2=area_m2, deposit=data.deposit, monthly=data.monthly,
            lat=lat, lng=lng, target_type=inferred_type_code,
        )
        return result
    except Exception as e:
        logger.error(f"[점수 평가 실패] {e}")
        return {"error": str(e)}


# ──────────────────────────────────────────────
# 가격 트렌드
# ──────────────────────────────────────────────

@router.get(
    "/market/trend",
    summary="지역 가격 트렌드 조회",
    description=(
        "지역명과 유형을 입력하면 날짜별 평균 환산가격 추이를 반환합니다.\n\n"
        "데이터는 listings/search 또는 listings/all 조회 시 DB에 축적됩니다.\n\n"
        "Query Parameters:\n\n"
        "- query (필수): 지역명. 예) 마포구\n"
        "- type (선택): 매물 유형 필터. 예) 원룸\n\n"
        "Response:\n\n"
        "- trend: [ { date, avg_price(만원), count } ] — 날짜 오름차순"
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


# ──────────────────────────────────────────────
# 즐겨찾기
# ──────────────────────────────────────────────

@router.post(
    "/favorites",
    summary="즐겨찾기 추가",
    description=(
        "매물 ID를 즐겨찾기에 추가합니다.\n\n"
        "Request Body:\n\n"
        "- user_id (필수): 사용자 식별자. 앱에서 관리하는 고유값을 사용하세요.\n"
        "- listing_id (필수): 즐겨찾기할 매물 ID (listings/search 응답의 id 필드)\n\n"
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
    description=(
        "user_id에 해당하는 즐겨찾기 매물 목록을 반환합니다.\n\n"
        "Path Variable:\n\n"
        "- user_id (필수): 사용자 식별자\n\n"
        "Response: 즐겨찾기 순으로 정렬된 매물 목록 (listings 테이블과 JOIN)"
    ),
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
        "Path Variable:\n\n"
        "- favorite_id (필수): 즐겨찾기 항목 ID (favorites 생성 응답의 id 필드)\n\n"
        "Query Parameter:\n\n"
        "- user_id (필수): 본인 항목만 삭제 가능합니다.\n\n"
        "삭제 성공 시 deleted: true를 반환합니다."
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


# ──────────────────────────────────────────────
# AI 추천 매물
# ──────────────────────────────────────────────

@router.post(
    "/recommend",
    summary="조건 기반 추천 매물 조회",
    description=(
        "예산·면적·유형 조건을 입력하면 해당 지역에서 가성비가 높은 매물을 추천합니다.\n\n"
        "Request Body:\n\n"
        "- query (필수): 지역명 또는 주소. 예) 마포구\n"
        "- max_deposit (선택): 최대 보증금 (만원)\n"
        "- max_monthly (선택): 최대 월세 (만원)\n"
        "- min_area_pyeong (선택): 최소 면적 (평)\n"
        "- preferred_types (선택): 선호 유형 목록. 예) ['원룸', '빌라']\n"
        "- top_n (선택, 기본 5): 추천 매물 수 (최대 20)\n\n"
        "Response:\n\n"
        "- recommendations: 가성비(단위면적당 가격) 순 정렬된 매물 목록\n"
        "- each item: id, address, area_m2, area_pyeong, deposit, monthly, price, price_per_m2, type, lat, lng"
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

        filtered = []
        for l in listings:
            if data.max_deposit is not None and l.get("deposit", 0) > data.max_deposit:
                continue
            if data.max_monthly is not None and l.get("monthly", 0) > data.max_monthly:
                continue
            if min_area_m2 is not None and l.get("area", 0) < min_area_m2:
                continue
            filtered.append(l)

        # 가성비 정렬: 단위면적당 환산가격 낮을수록 상위
        def price_per_m2(l):
            area = l.get("area") or 1
            return l.get("price", 0) / area

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

        logger.info(f"[추천 매물] {data.query} 조건 충족 {len(filtered)}건 중 {len(recommendations)}건 반환 {time.perf_counter() - start:.2f}초")
        return {"query": data.query, "total_filtered": len(filtered), "recommendations": recommendations}
    except Exception as e:
        logger.error(f"[추천 매물 실패] {e}")
        return {"error": str(e)}
