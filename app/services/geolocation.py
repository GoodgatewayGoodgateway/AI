import os
import httpx
from dotenv import load_dotenv

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
