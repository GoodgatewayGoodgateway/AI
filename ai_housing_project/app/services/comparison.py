from app.schemas import HousingRequest, ComparisonResult, SimilarListing

# 가짜 유사 매물 리스트 (예: 같은 지역, 같은 유형 등)
fake_similar_listings = [
    {"address": "서울시 강남구 역삼동 123-1", "price": 850, "area": 27.0, "lat": 37.5005, "lng": 127.0311},
    {"address": "서울시 강남구 삼성동 201-2", "price": 890, "area": 28.5, "lat": 37.5012, "lng": 127.0308},
    {"address": "서울시 강남구 논현동 77-3", "price": 870, "area": 26.5, "lat": 37.4989, "lng": 127.0320},
    {"address": "서울시 강남구 청담동 19-5", "price": 900, "area": 29.0, "lat": 37.4971, "lng": 127.0332},
]

def compare_with_similars(current: HousingRequest) -> ComparisonResult:
    total_price = sum(m["price"] for m in fake_similar_listings)
    total_area = sum(m["area"] for m in fake_similar_listings)
    count = len(fake_similar_listings)

    avg_price = round(total_price / count)
    avg_area = round(total_area / count, 1)
    cheaper = current.price < avg_price

    similar_list = [
        SimilarListing(
            address=m["address"],
            area=m["area"],
            price=m["price"],
            lat=m["lat"],
            lng=m["lng"]
        )
        for m in fake_similar_listings
    ]

    return ComparisonResult(
        cheaper_than_average=cheaper,
        average_price=avg_price,
        average_area=avg_area,
        similar_listings=similar_list
    )