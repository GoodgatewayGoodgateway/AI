from app.schemas import ComparisonResult, SimilarListing
from src.classes import NLocation
from src.util import (
    get_sector,
    async_get_parallel_things,
    distance_between,
    get_article_listings
)

async def compare_with_similars(area: float, deposit: int, monthly: int, lat: float, lng: float, target_type: str) -> ComparisonResult:
    current_price = deposit + (monthly * 10)
    current_loc = NLocation(lat, lng)

    # 1. 섹터 조회
    try:
        sector = get_sector(current_loc)
    except Exception as e:
        raise RuntimeError(f"섹터 정보를 불러오지 못했습니다: {e}")

    # 2. 매물 크롤링
    if target_type == "OR":  # 원룸일 경우 article API 사용
        things = await get_article_listings(current_loc)
        # 필터링된 article dict 리스트 → SimilarListing으로 변환
        valid_listings = [
            SimilarListing(
                address=t["address"],
                area=t["area"],
                deposit=t["deposit"],
                monthly=t["monthly"],
                price=t["price"],
                lat=t["lat"],
                lng=t["lng"],
                distance_km=t["distance_km"]
            )
            for t in things if t["area"] and t["deposit"] is not None
        ]
    else:  # 그 외는 complex API 사용
        try:
            complex_things = await async_get_parallel_things(sector)
        except Exception as e:
            raise RuntimeError(f"복합 단지 매물을 불러오지 못했습니다: {e}")

        valid_listings = []
        for t in complex_things:
            if t.lease.mn is None or t.area.representative is None:
                continue
            if t.type != target_type:
                continue

            area_m2 = round(t.area.representative * 3.3, 1)
            distance_km = round(distance_between(current_loc, t.loc) / 1000, 2)
            valid_listings.append(SimilarListing(
                address=t.name,
                area=area_m2,
                deposit=t.lease.mn,
                monthly=0,
                price=t.lease.mn,
                lat=t.loc.lat,
                lng=t.loc.lon,
                distance_km=distance_km
            ))

    if not valid_listings:
        raise ValueError("해당 유형의 유사 매물을 찾을 수 없습니다.")

    # 평균 계산
    total_price = sum(t.price for t in valid_listings)
    total_area = sum(t.area for t in valid_listings)
    count = len(valid_listings)

    avg_price = round(total_price / count)
    avg_area = round(total_area / count, 1)
    cheaper = current_price < avg_price

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=valid_listings
    )