"""
라우터 공통 유틸리티 — 모든 라우터 파일에서 import해서 사용.
"""
import asyncio
import logging
import requests
from typing import Optional

from app.services.geolocation import address_to_coords

logger = logging.getLogger(__name__)

# ── 단위 변환 ──────────────────────────────────────────────
def pyeong_to_m2(pyeong: float) -> float:
    return round(pyeong * 3.3, 1)

def to_pyeong(area_m2: float) -> float:
    return round(area_m2 / 3.3, 1)

# ── 매물 유형 코드 매핑 ────────────────────────────────────
TYPE_LABEL_TO_CODE: dict = {
    "아파트": "APT",   "APT": "APT",   "A01": "APT",
    "오피스텔": "OPST", "OPST": "OPST", "A02": "OPST",
    "원룸": "OR",      "OR": "OR",     "C01": "OR",
    "빌라": "VL",      "VL": "VL",     "다세대주택": "VL",
    "다가구": "DDDGG", "DDDGG": "DDDGG", "다가구주택": "DDDGG",
    "주택": "HOJT",   "HOJT": "HOJT", "단독주택": "HOJT",
    "연립주택": "JWJT","JWJT": "JWJT",
}

# ── 전국 주요 도시 중심 좌표 ───────────────────────────────
CITY_CENTERS: dict = {
    "서울": (37.5665, 126.9780),
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "대전": (36.3504, 127.3845),
    "광주": (35.1595, 126.8526),
    "인천": (37.4563, 126.7052),
    "제주": (33.4996, 126.5312),
    "수원": (37.2635, 127.0286),
    "울산": (35.5384, 129.3114),
    "창원": (35.2285, 128.6865),
    "청주": (36.6359, 127.4914),
    "천안": (36.8149, 127.1192),
    "전주": (35.8200, 127.1523),
}

# ── Swagger 공통 파라미터 설명 ─────────────────────────────
TYPES_QUERY_DESC = (
    "매물 유형 필터 (선택, 반복 입력 가능).\n"
    "입력하지 않으면 전체 유형을 반환합니다.\n\n"
    "사용 가능한 값:\n"
    "- 원룸 (또는 OR)\n"
    "- 빌라 (또는 VL)\n"
    "- 오피스텔 (또는 OPST)\n"
    "- 아파트 (또는 APT)\n"
    "- 다가구 (또는 DDDGG)\n"
    "- 주택 (또는 HOJT)\n"
    "- 연립주택 (또는 JWJT)"
)

# ── 매물 리스트 캐시 (단일 프로세스 기준) ─────────────────
listing_query_cache: dict = {"query": None, "listings": []}
listing_cache_ttl: int = 60
listing_cache_time: Optional[float] = None
cached_listings: list = []

# ── 유형 추론 캐시 ─────────────────────────────────────────
_type_cache: dict = {}


async def infer_type_from_address(address: str) -> str:
    """
    주소 기반 매물 유형 자동 추론.
    동기 requests를 asyncio.to_thread로 감싸 이벤트 루프 블로킹 방지.
    """
    if address in _type_cache:
        return _type_cache[address]

    lat, lng = await address_to_coords(address)
    url = "https://m.land.naver.com/cluster/ajax/articleList"
    params = {
        "rletTpCd": "APT:OPST:VL:DDDGG:HOJT:JWJT:OR",
        "tradTpCd": "A1:B1:B2",
        "z": 16, "lat": lat, "lon": lng,
        "btm": lat - 0.002, "lft": lng - 0.002,
        "top": lat + 0.002, "rgt": lng + 0.002,
        "page": 1,
    }

    def _fetch() -> dict:
        res = requests.get(
            url, params=params,
            headers={"User-Agent": "Mozilla/5.0"}, timeout=5,
        )
        return res.json()

    try:
        data = await asyncio.to_thread(_fetch)
        if data.get("body"):
            inferred = data["body"][0].get("rletTpNm", "기타")
            _type_cache[address] = inferred
            return inferred
    except Exception:
        pass
    return "기타"
