import asyncio
from app.services.comparison import compare_with_similars
from app.services.facilities import async_get_nearby_facilities


async def calculate_score(
    area_m2: float,
    deposit: int,
    monthly: int,
    lat: float,
    lng: float,
    target_type: str,
) -> dict:
    """
    매물 종합 점수 산출.

    가중치:
      - 가격 점수 50%: 시세 대비 저렴할수록 높음
      - 편의시설 점수 30%: 반경 1500m 내 카페·편의점·병원 등 수
      - 교통 점수 20%: 반경 1500m 내 지하철역 수
    """
    cmp_result, fac_dict = await asyncio.gather(
        compare_with_similars(
            area=area_m2, deposit=deposit, monthly=monthly,
            lat=lat, lng=lng, target_type=target_type,
        ),
        async_get_nearby_facilities(lat, lng),
    )

    # 가격 점수 (0~100)
    input_price = deposit + monthly * 10
    avg_price = (
        cmp_result.get("average_price", input_price)
        if isinstance(cmp_result, dict)
        else cmp_result.average_price
    )
    if avg_price > 0:
        ratio = input_price / avg_price
        if ratio <= 0.8:
            price_score = 100
        elif ratio >= 1.2:
            price_score = 0
        else:
            price_score = int((1.2 - ratio) / 0.4 * 100)
    else:
        price_score = 50

    # 편의시설 점수 (0~100): 비교통 카테고리 합산, 40개 이상 → 100점
    facility_count = sum(
        len(fac_dict.get(cat, []))
        for cat in ["cafes", "convenience_stores", "gyms", "schools", "hospitals", "banks", "parks"]
    )
    facilities_score = min(100, int(facility_count / 40 * 100))

    # 교통 점수 (0~100): 지하철역 5개 이상 → 100점
    transit_count = len(fac_dict.get("subway_stations", []))
    transit_score = min(100, int(transit_count / 5 * 100))

    total = int(price_score * 0.5 + facilities_score * 0.3 + transit_score * 0.2)

    if total >= 90:
        grade = "S"
    elif total >= 80:
        grade = "A"
    elif total >= 70:
        grade = "B"
    elif total >= 60:
        grade = "C"
    elif total >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "total_score": total,
        "breakdown": {
            "price_score": price_score,
            "facilities_score": facilities_score,
            "transit_score": transit_score,
        },
        "grade": grade,
    }
