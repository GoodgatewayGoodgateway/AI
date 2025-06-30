# app/routes/housing_detail.py

import logging
import re, json, math
import requests
from fastapi import APIRouter, Body, Query
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from app.services.geolocation import address_to_coords, coords_to_address
from app.services.facilities import get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary
from src.classes import NLocation
from src.util import get_sector, get_things_each_direction, distance_between

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

@router.get(
    "/facilities",
    summary="주변 편의시설 조회",
    description="주소 또는 좌표를 기반으로 주변 카페, 편의점, 헬스장을 조회합니다.",
    response_description="FacilitySummary 객체 반환"
)
def get_facilities(query: str = Query(..., description="주소 (예: 대구 달서구 상인동)")):
    try:
        lat, lng = address_to_coords(query)
        facilities = get_nearby_facilities(lat, lng)
        logger.info(f"[편의시설 조회] lat={lat}, lng={lng}")
        return facilities.dict()
    except Exception as e:
        logger.error(f"[편의시설 조회 실패] {e}")
        return {"error": str(e)}

@router.post(
    "/summary",
    summary="AI 요약 문장 생성",
    description="입력한 매물, 주변시설, 비교 정보를 바탕으로 AI가 요약 문장을 생성합니다.",
    response_description="요약 문장"
)
def get_ai_summary(data: HousingRequest = Body(...)):
    try:
        lat, lng = address_to_coords(data.address)
        area_m2 = pyeong_to_m2(data.netLeasableArea)
        facilities = get_nearby_facilities(lat, lng)
        comparison = compare_with_similars(
            area=area_m2,
            deposit=data.deposit,
            monthly=data.monthly,
            lat=lat,
            lng=lng
        )
        summary = generate_summary(data, facilities, comparison)
        logger.info(f"[요약 문장] {summary}")
        return {"summary": summary}
    except Exception as e:
        logger.error(f"[요약 생성 실패] {e}")
        return {"error": str(e)}

@router.get(
    "/listings/search",
    summary="지역 기반 매물 검색",
    description="지역명(동, 역, 학교 등)을 입력하면 해당 위치 주변의 매물 리스트를 반환합니다.",
    response_description="매물 리스트"
)
def search_listings(query: str = Query(..., description="지역명 또는 키워드")):
    try:
        # 주소 → 좌표 변환
        lat, lng = address_to_coords(query)
        loc = NLocation(lat, lng)
        listings = []

        # 1. complex 매물 (APT, OPST 등)
        try:
            sector = get_sector(loc)
            complex_things = get_things_each_direction(sector)
            for t in complex_things:
                if t.lease.mn is None or t.area.representative is None:
                    continue
                lat_c = t.loc.lat
                lng_c = t.loc.lon
                address_name = coords_to_address(lat_c, lng_c)
                
                TYPE_LABELS = {
                "APT": "아파트",
                "OPST": "오피스텔",
                "VL": "빌라",
                "DDDGG": "다가구",
                "HOJT": "주택",
                "JWJT": "연립주택",
                "OR": "원룸",
            }

                listings.append({
                    "name": t.name,  # 단지명 → name
                    "address": address_name,  # Kakao 주소
                    "area": round(t.area.representative * 3.3, 1),
                    "deposit": t.lease.mn,
                    "monthly": 0,
                    "price": t.lease.mn,
                    "lat": lat_c,
                    "lng": lng_c,
                    "type": TYPE_LABELS.get(t.type, "기타"),
                    "distance_km": round(distance_between(loc, t.loc) / 1000, 2),
                    "source": "complex"
                })
        except Exception as e:
            logger.warning(f"[complex 크롤링 실패] {e}")

        # 2. article 매물 (빌라, 원룸, 단독 등)
        try:
            url = "https://m.land.naver.com/cluster/ajax/articleList"
            params = {
                "rletTpCd": "VL:DDDGG:HOJT:JWJT:OR",
                "tradTpCd": "A1:B1:B2",
                "z": 16,
                "lat": lat,
                "lon": lng,
                "btm": lat - 0.005,
                "lft": lng - 0.01,
                "top": lat + 0.005,
                "rgt": lng + 0.01,
                "page": 1
            }
            res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
            data = res.json()

            for a in data["body"]:
                try:
                    deposit = int(a.get("prc", 0))
                    monthly = int(a.get("rentPrc", 0))
                    area_m2 = float(a.get("spc2", 0) or 0.0)
                    lat_a = float(a["lat"])
                    lng_a = float(a["lng"])
                    address_name = coords_to_address(lat_a, lng_a)

                    listings.append({
                        "name": a.get("atclNm", "매물"),
                        "address": address_name,
                        "area": round(area_m2, 1),
                        "deposit": deposit,
                        "monthly": monthly,
                        "price": deposit + monthly * 10,
                        "lat": lat_a,
                        "lng": lng_a,
                        "type": a.get("rletTpNm", "기타"),
                        "distance_km": round(distance_between(loc, NLocation(lat_a, lng_a)) / 1000, 2),
                        "source": "article"
                    })
                except Exception as e:
                    logger.warning(f"[article 파싱 실패] {e}")
        except Exception as e:
            logger.warning(f"[articleList 요청 실패] {e}")

        return {"listings": listings}

    except Exception as e:
        logger.error(f"[지역 검색 오류] {str(e)}")
        return {"error": str(e)}
