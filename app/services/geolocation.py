import logging
import os
import httpx
from dotenv import load_dotenv
import requests

load_dotenv()  # .env에서 API 키 로드

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

def address_to_coords(address: str) -> tuple[float, float]:
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

    return y, x

def reverse_geocode(lat: float, lng: float) -> str:
    try:
        kakao_key = os.getenv("KAKAO_REST_API_KEY")
        headers = {"Authorization": f"KakaoAK {kakao_key}"}
        params = {"x": lng, "y": lat}
        res = httpx.get("https://dapi.kakao.com/v2/local/geo/coord2address.json", headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        return data["documents"][0]["address"]["address_name"]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"[reverse_geocode 실패] {e}")
        return "주소 미상"

def coords_to_address(lat: float, lng: float) -> str:
    try:
        kakao_key = os.getenv("KAKAO_REST_API_KEY")
        headers = {"Authorization": f"KakaoAK {kakao_key}"}
        res = requests.get(
            f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={lng}&y={lat}",
            headers=headers,
            timeout=3
        )
        res.raise_for_status()
        documents = res.json().get("documents", [])
        if not documents:
            return "주소 미상"
        return documents[0]["address"].get("address_name", "주소 미상")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"[주소 변환 실패] {e}")
        return "주소 미상"