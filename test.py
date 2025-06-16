import os
import httpx
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("KAKAO_REST_API_KEY")
headers = {"Authorization": f"KakaoAK {key}"}
params = {"query": "서울특별시 강남구 테헤란로 123"}

res = httpx.get("https://dapi.kakao.com/v2/local/search/address.json", headers=headers, params=params)
print(res.status_code)
print(res.json())
