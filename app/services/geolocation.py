import logging
import os
import httpx
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

_address_cache = {}
_coords_cache = {}

def address_to_coords(address: str) -> tuple[float, float]:
    if address in _address_cache:
        return _address_cache[address]

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }
    params = {"query": address}

    with httpx.Client() as client:
        response = client.get(GEOCODE_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    documents = data.get("documents")
    if not documents:
        raise ValueError("주소를 찾을 수 없습니다.")

    x = float(documents[0]["x"])  # 경도
    y = float(documents[0]["y"])  # 위도

    _address_cache[address] = (y, x)
    return y, x

def coords_to_address(lat: float, lng: float) -> str:
    key = f"{lat:.5f},{lng:.5f}"
    if key in _coords_cache:
        return _coords_cache[key]

    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        res = requests.get(
            f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={lng}&y={lat}",
            headers=headers,
            timeout=3
        )
        res.raise_for_status()
        documents = res.json().get("documents", [])
        if not documents:
            return "주소 미상"
        address = documents[0]["address"].get("address_name", "주소 미상")
        _coords_cache[key] = address
        return address
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"[주소 변환 실패] {e}")
        return "주소 미상"
