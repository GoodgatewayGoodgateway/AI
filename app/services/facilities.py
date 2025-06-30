import os
import httpx
from dotenv import load_dotenv
from app.schemas import FacilityItem, FacilitySummary

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

CATEGORIES = {
    "cafes": "CE7",                 # 카페
    "convenience_stores": "CS2",   # 편의점
    "gyms": "CT1",                  # 헬스장/문화시설
    "subway_stations": "SW8",      # 지하철역
    "schools": "SC4",              # 학교
    "hospitals": "HP8",            # 병원
    "banks": "BK9",                # 은행
    "parks": "PK6",                # 공원
}

KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

def get_keyword_items(lat: float, lng: float, keyword: str, radius: int = 500, limit: int = None) -> list[FacilityItem]:
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "query": keyword,
        "x": lng,
        "y": lat,
        "radius": radius,
        "size": 15
    }

    with httpx.Client() as client:
        response = client.get(KEYWORD_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    docs = data.get("documents", [])
    if limit:
        docs = docs[:limit]

    items = [
        FacilityItem(
            name=doc.get("place_name"),
            lat=float(doc.get("y")),
            lng=float(doc.get("x"))
        )
        for doc in docs
    ]
    return items

def get_category_items(lat: float, lng: float, category_code: str, radius: int = 1500, limit: int = None) -> list[FacilityItem]:
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "category_group_code": category_code,
        "x": lng,
        "y": lat,
        "radius": radius,
        "size": 15
    }

    with httpx.Client() as client:
        response = client.get(CATEGORY_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    docs = data.get("documents", [])
    if limit:
        docs = docs[:limit]

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
        cafes=get_category_items(lat, lng, CATEGORIES["cafes"]),
        convenience_stores=get_category_items(lat, lng, CATEGORIES["convenience_stores"]),
        gyms=get_category_items(lat, lng, CATEGORIES["gyms"]),
        subway_stations=get_category_items(lat, lng, CATEGORIES["subway_stations"]),
        schools=get_category_items(lat, lng, CATEGORIES["schools"]),
        hospitals=get_category_items(lat, lng, CATEGORIES["hospitals"]),
        banks=get_category_items(lat, lng, CATEGORIES["banks"]),
        parks=get_category_items(lat, lng, CATEGORIES["parks"])
        # bus_stops=get_keyword_items(lat, lng, keyword="정류장")
    )
