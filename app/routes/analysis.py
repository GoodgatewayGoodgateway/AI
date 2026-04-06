import asyncio
import logging
import time

from fastapi import APIRouter, Body
from app.schemas import HousingRequest, FacilitySummary, ComparisonResult
from app.services.geolocation import address_to_coords
from app.services.facilities import async_get_nearby_facilities
from app.services.comparison import compare_with_similars
from app.services.summary import generate_summary
from app.services.score import calculate_score
from app.routes._shared import pyeong_to_m2, to_pyeong, TYPE_LABEL_TO_CODE, infer_type_from_address

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/comparison",
    summary="유사 매물 비교",
    description=(
        "입력한 매물을 주변 유사 매물들과 가격·면적 기준으로 비교합니다.\n\n"
        "Request Body:\n\n"
        "- address (필수): 매물 주소. 도로명·지번 모두 가능합니다.\n"
        "- netLeasableArea (필수): 전용면적 (평 단위)\n"
        "- deposit (필수): 보증금 (만원)\n"
        "- monthly (필수): 월세 (만원). 매매·전세는 0\n"
        "- type (선택): 입력하지 않으면 주소 기반으로 자동 추론\n\n"
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

        fac_dict, cmp_result = await asyncio.gather(
            async_get_nearby_facilities(lat, lng),
            compare_with_similars(
                area=area_m2, deposit=data.deposit, monthly=data.monthly,
                lat=lat, lng=lng, target_type=inferred_type_code,
            ),
        )

        fac = FacilitySummary(**fac_dict)
        cmp = ComparisonResult(**cmp_result) if isinstance(cmp_result, dict) else cmp_result
        summary = await generate_summary(data, fac, cmp)

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
        "각 항목은 name, lat, lng 필드를 포함합니다."
    ),
    response_description="8개 카테고리별 편의시설 목록",
)
async def get_facilities(query: str):
    start = time.perf_counter()
    try:
        lat, lng = await address_to_coords(query)
        fac_dict = await async_get_nearby_facilities(lat, lng)
        logger.info(f"[편의시설 조회 완료] {time.perf_counter() - start:.2f}초 소요")
        return fac_dict
    except Exception as e:
        logger.error(f"[편의시설 조회 실패] {e}")
        return {"error": str(e)}


@router.post(
    "/score",
    summary="매물 종합 점수 평가",
    description=(
        "매물 정보를 입력하면 가격·편의시설·교통을 종합한 점수(0~100)와 등급을 반환합니다.\n\n"
        "가중치: 가격 50% + 편의시설 30% + 교통(지하철) 20%\n\n"
        "등급: S(90+) / A(80+) / B(70+) / C(60+) / D(50+) / F"
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
