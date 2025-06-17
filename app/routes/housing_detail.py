# app/routes/housing_detail.py

import logging
from fastapi import APIRouter, Body
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from app.services.geolocation import address_to_coords
from app.services.facilities import get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary  # ✅ Gemini 요약 함수

# 기본 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/recommendation",
    summary="부동산 AI 추천 + AI 요약",
    description="주소, 면적, 가격을 입력하면 해당 매물의 주변 편의시설, 유사 매물 비교 결과, 요약 문장을 함께 반환합니다.",
    response_description="추천 분석 결과 (좌표, 시설 목록, 유사 매물 정보, AI 요약 문장 포함)"
)
def get_full_housing_analysis(data: HousingRequest = Body(...)):
    logger.info(f"[요청 받은 매물] 주소: {data.address}, 면적: {data.area}, 가격: {data.price}")

    # 위경도 변환
    lat, lng = address_to_coords(data.address)
    logger.info(f"[위치 변환 완료] 위도: {lat}, 경도: {lng}")

    # 주변 편의시설 수집
    facilities: FacilitySummary = get_nearby_facilities(lat, lng)
    logger.info(f"[주변 편의시설] 카페: {len(facilities.cafes)}, 편의점: {len(facilities.convenience_stores)}, 헬스장: {len(facilities.gyms)}")

    # 유사 매물 비교
    comparison: ComparisonResult = compare_with_similars(data)
    cheaper = "저렴함" if comparison.cheaper_than_average else "비슷하거나 비쌈"
    logger.info(f"[유사 매물 평균] 가격: {comparison.average_price}만원, 면적: {comparison.average_area}㎡ → 현재 매물은 {cheaper}")

    # AI 요약 생성
    summary = generate_summary(data, facilities, comparison)
    logger.info(f"[AI 요약] {summary}")

    return {
        "coords": {"lat": lat, "lng": lng},
        "facilities": facilities.dict(),
        "comparison": comparison.dict(),
        "summary": summary
    }
