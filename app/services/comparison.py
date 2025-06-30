from app.schemas import ComparisonResult, SimilarListing
from app.utils.distance import haversine
from src.classes import NLocation
from src.util import get_sector, get_things_each_direction, distance_between

def compare_with_similars(area: float, deposit: int, monthly: int, lat: float, lng: float) -> ComparisonResult:
    # 현재 매물의 정보
    current_price = deposit + (monthly * 10)
    current_loc = NLocation(lat, lng)

    # 섹터 조회
    try:
        sector = get_sector(current_loc)
    except Exception as e:
        raise RuntimeError(f"섹터 정보를 불러오지 못했습니다: {e}")

    # 실매물 수집 (방향별)
    try:
        things = get_things_each_direction(sector)
    except Exception as e:
        raise RuntimeError(f"실매물 정보를 불러오지 못했습니다: {e}")

    # 유효 매물만 필터링
    valid_things = [t for t in things if t.lease.mn is not None and t.area.representative is not None]

    if not valid_things:
        raise ValueError("해당 위치에서 유사 매물을 찾을 수 없습니다.")

    similar_listings = []
    total_price = 0
    total_area = 0

    for t in valid_things:
        price = t.lease.mn  # 전세가
        area_m2 = round(t.area.representative * 3.3, 1)
        total_price += price
        total_area += area_m2

        distance_km = distance_between(current_loc, t.loc) / 1000  # m → km

        similar = SimilarListing(
            address=t.name,
            area=area_m2,
            deposit=price,
            monthly=0,
            price=price,
            lat=t.loc.lat,
            lng=t.loc.lon,
            distance_km=round(distance_km, 2)
        )
        similar_listings.append(similar)

    count = len(similar_listings)
    avg_price = round(total_price / count)
    avg_area = round(total_area / count, 1)
    cheaper = current_price < avg_price

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=similar_listings
    )
