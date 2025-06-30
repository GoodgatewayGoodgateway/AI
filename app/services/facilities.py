import os
import asyncio
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

async def fetch_category(client, lat, lng, category_code):
    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {
        "category_group_code": category_code,
        "x": lng,
        "y": lat,
        "radius": 1500,
        "size": 15
    }
    resp = await client.get(CATEGORY_URL, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def add_id_to_items(items: list[FacilityItem]) -> list[dict]:
    return [
        {
            "id": i,
            "name": item.name,
            "lat": item.lat,
            "lng": item.lng
        }
        for i, item in enumerate(items)
    ]

async def async_get_nearby_facilities(lat: float, lng: float) -> dict:
    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_category(client, lat, lng, code)
            for code in CATEGORIES.values()
        ]
        responses = await asyncio.gather(*tasks)

    results = {}
    for name, resp in zip(CATEGORIES.keys(), responses):
        items = [
            FacilityItem(
                name=doc.get("place_name"),
                lat=float(doc.get("y")),
                lng=float(doc.get("x"))
            )
            for doc in resp.get("documents", [])
        ]
        results[name] = add_id_to_items(items)
    return results

# 동기 fallback 함수 (기존과 동일하게 유지)
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

def get_nearby_facilities(lat: float, lng: float) -> dict:
    return {
        "cafes": add_id_to_items(get_category_items(lat, lng, CATEGORIES["cafes"])),
        "convenience_stores": add_id_to_items(get_category_items(lat, lng, CATEGORIES["convenience_stores"])),
        "gyms": add_id_to_items(get_category_items(lat, lng, CATEGORIES["gyms"])),
        "subway_stations": add_id_to_items(get_category_items(lat, lng, CATEGORIES["subway_stations"])),
        "schools": add_id_to_items(get_category_items(lat, lng, CATEGORIES["schools"])),
        "hospitals": add_id_to_items(get_category_items(lat, lng, CATEGORIES["hospitals"])),
        "banks": add_id_to_items(get_category_items(lat, lng, CATEGORIES["banks"])),
        "parks": add_id_to_items(get_category_items(lat, lng, CATEGORIES["parks"]))
    }
