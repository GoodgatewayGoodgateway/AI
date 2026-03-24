import asyncio
from app.schemas import ComparisonResult, SimilarListing
from src.classes import NLocation
from src.util import distance_between, get_article_listings

# 유형 코드 → 표시명 매핑 (필터용)
_TYPE_NAME_MAP = {
    "APT":   ["아파트"],
    "OPST":  ["오피스텔"],
    "OR":    ["원룸"],
    "VL":    ["빌라", "다세대주택"],
    "DDDGG": ["다가구주택", "다가구"],
    "HOJT":  ["단독주택", "주택"],
    "JWJT":  ["연립주택"],
}

# 유형별 유사 그룹 (비슷한 유형끼리 묶어서 비교)
_TYPE_GROUP = {
    "APT":   {"APT"},
    "OPST":  {"OPST"},
    "OR":    {"OR"},
    "VL":    {"VL", "DDDGG", "JWJT"},
    "DDDGG": {"VL", "DDDGG", "JWJT"},
    "HOJT":  {"HOJT"},
    "JWJT":  {"VL", "DDDGG", "JWJT"},
}


def _type_names_for(target_type: str) -> set[str]:
    """비교 대상 유형 코드 집합 → 표시명 집합"""
    codes = _TYPE_GROUP.get(target_type, {target_type})
    names: set[str] = set()
    for code in codes:
        names.update(_TYPE_NAME_MAP.get(code, []))
    return names


async def compare_with_similars(
    area: float,
    deposit: int,
    monthly: int,
    lat: float,
    lng: float,
    target_type: str,
) -> ComparisonResult:
    current_price = deposit + (monthly * 10)
    current_loc = NLocation(lat, lng)

    # 전체 매물 조회 (APT 포함 모든 유형)
    things = await get_article_listings(current_loc, pages=2)

    # 유형 필터
    allowed_names = _type_names_for(target_type)
    if allowed_names:
        things = [t for t in things if t.get("type") in allowed_names]

    valid_listings = [
        SimilarListing(
            address=t["address"],
            area=t["area"],
            deposit=t["deposit"],
            monthly=t["monthly"],
            price=t["price"],
            lat=t["lat"],
            lng=t["lng"],
            distance_km=t["distance_km"],
        )
        for t in things
        if t.get("area") and t.get("deposit") is not None and t.get("price", 0) > 0
    ]

    if not valid_listings:
        raise ValueError("해당 유형의 유사 매물을 찾을 수 없습니다.")

    count = len(valid_listings)
    avg_price = round(sum(s.price for s in valid_listings) / count)
    avg_area = round(sum(s.area for s in valid_listings) / count, 1)
    cheaper = current_price < avg_price

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=valid_listings,
    )
