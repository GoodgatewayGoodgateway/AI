import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
GEOCODE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
REVERSE_GEOCODE_URL = "https://dapi.kakao.com/v2/local/geo/coord2address.json"

# 캐시
_address_cache: dict[str, tuple[float, float]] = {}
_coords_cache: dict[str, str] = {}

_shared_client: httpx.AsyncClient | None = None

def set_shared_client(client: httpx.AsyncClient):
    global _shared_client
    _shared_client = client

async def close_shared_client():
    global _shared_client
    if _shared_client:
        await _shared_client.aclose()
        _shared_client = None

async def address_to_coords(address: str) -> tuple[float, float]:
    if address in _address_cache:
        return _address_cache[address]

    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}

    try:
        resp = await _shared_client.get(GEOCODE_URL, headers=headers, params=params)
        resp.raise_for_status()
        documents = resp.json().get("documents", [])
        if not documents:
            raise ValueError(f"[주소 변환 실패] 결과 없음: {address}")
        x = float(documents[0]["x"])  # 경도
        y = float(documents[0]["y"])  # 위도
        _address_cache[address] = (y, x)
        return y, x
    except Exception as e:
        logger.warning(f"[주소 변환 실패] {e}")
        raise

async def coords_to_address(lat: float, lng: float) -> str:
    global _shared_client
    if _shared_client is None:
        raise RuntimeError("HTTP client is not initialized")

    key = f"{lat:.5f},{lng:.5f}"
    if key in _coords_cache:
        return _coords_cache[key]

    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"x": lng, "y": lat}
        response = await _shared_client.get(REVERSE_GEOCODE_URL, headers=headers, params=params)
        response.raise_for_status()
        documents = response.json().get("documents", [])
        if not documents:
            return "주소 미상"
        address = documents[0]["address"].get("address_name", "주소 미상")
        _coords_cache[key] = address
        return address
    except Exception as e:
        logger.warning(f"[주소 변환 실패] {e}")
        return "주소 미상"
