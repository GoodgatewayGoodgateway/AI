import os
import httpx
from dotenv import load_dotenv
from app.schemas import FacilityItem, FacilitySummary

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

# Kakao 지도 카테고리 코드
CATEGORIES = {
    "cafes": "CE7",             # 카페
    "convenience_stores": "CS2", # 편의점
    "gyms": "CT1"               # 문화시설로 대체 가능
}

def get_category_count(lat: float, lng: float, category_code: str, radius: int = 500) -> int:
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "category_group_code": category_code,
        "x": lng,
        "y": lat,
        "radius": radius
    }

    with httpx.Client() as client:
        response = client.get(CATEGORY_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    return len(data.get("documents", []))

def get_category_items(lat: float, lng: float, category_code: str, radius: int = 500, limit: int = None) -> list[FacilityItem]:
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "category_group_code": category_code,
        "x": lng,
        "y": lat,
        "radius": radius,
        "size": 15  # Kakao 제한: 1페이지 최대 15개
    }

    with httpx.Client() as client:
        response = client.get(CATEGORY_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    docs = data.get("documents", [])
    if limit:
        docs = docs[:limit]  # 제한 있을 경우만 자름

    items = [
        FacilityItem(
            name=doc.get("place_name"),
            lat=float(doc.get("y")),
            lng=float(doc.get("x"))
        )
        for doc in docs
    ]

    return items

def get_nearby_facilities(lat: float, lng: float) -> FacilitySummary:
    return FacilitySummary(
        cafes=get_category_items(lat, lng, CATEGORIES["cafes"], limit=None),
        convenience_stores=get_category_items(lat, lng, CATEGORIES["convenience_stores"], limit=None),
        gyms=get_category_items(lat, lng, CATEGORIES["gyms"], limit=None)
    )

