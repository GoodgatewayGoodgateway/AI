from app.schemas import ComparisonResult, SimilarListing
from app.utils.distance import haversine

# 면적은 ㎡ 단위, 보증금 + 월세 구조 (전용면적 기준)
fake_similar_listings = [
    {
        "address": "서울시 강남구 역삼동 123-1",
        "netLeasableArea": 8.2,     # 평수
        "area": round(8.2 * 3.3, 1),  # ㎡ 변환
        "deposit": 2000,
        "monthly": 65,
        "lat": 37.5005,
        "lng": 127.0311
    },
    {
        "address": "서울시 강남구 삼성동 201-2",
        "netLeasableArea": 8.6,
        "area": round(8.6 * 3.3, 1),
        "deposit": 1500,
        "monthly": 70,
        "lat": 37.5012,
        "lng": 127.0308
    },
    {
        "address": "서울시 강남구 논현동 77-3",
        "netLeasableArea": 8.0,
        "area": round(8.0 * 3.3, 1),
        "deposit": 1000,
        "monthly": 80,
        "lat": 37.4989,
        "lng": 127.0320
    },
    {
        "address": "서울시 강남구 청담동 19-5",
        "netLeasableArea": 8.8,
        "area": round(8.8 * 3.3, 1),
        "deposit": 1800,
        "monthly": 75,
        "lat": 37.4971,
        "lng": 127.0332
    },
]

def compare_with_similars(area: float, deposit: int, monthly: int, lat: float, lng: float) -> ComparisonResult:
    # 현재 매물의 "실질 가격"
    current_price = deposit + (monthly * 10)

    # 평균 계산
    total_price = sum(m["deposit"] + (m["monthly"] * 10) for m in fake_similar_listings)
    total_area = sum(m["area"] for m in fake_similar_listings)
    count = len(fake_similar_listings)

    avg_price = round(total_price / count)
    avg_area = round(total_area / count, 1)
    cheaper = current_price < avg_price

    # 유사 매물 리스트 구성
    similar_list = [
        SimilarListing(
            address=m["address"],
            area=m["area"],
            deposit=m["deposit"],
            monthly=m["monthly"],
            price=m["deposit"] + (m["monthly"] * 10),
            lat=m["lat"],
            lng=m["lng"],
            distance_km=haversine(lat, lng, m["lat"], m["lng"])
        )
        for m in fake_similar_listings
    ]

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=similar_list
    )
