from pydantic import BaseModel, Field
from typing import List, Optional


# ──────────────────────────────────────────────
# 요청 스키마
# ──────────────────────────────────────────────

class HousingRequest(BaseModel):
    address: str = Field(
        ...,
        description="매물 주소 (도로명 또는 지번 모두 가능)",
        examples=["서울시 마포구 합정동", "대구광역시 달서구 월곡로 320"],
    )
    netLeasableArea: float = Field(
        ...,
        description="전용면적 (평 단위). ㎡로 변환하려면 × 3.3",
        examples=[18.5],
    )
    deposit: int = Field(
        ...,
        description="보증금 (만원 단위). 매매의 경우 매매가를 입력",
        examples=[1000],
    )
    monthly: int = Field(
        ...,
        description="월세 (만원 단위). 매매·전세의 경우 0 입력",
        examples=[50],
    )
    type: Optional[str] = Field(
        None,
        description=(
            "매물 유형 (선택). 입력하지 않으면 주소 기반으로 자동 추론합니다.\n\n"
            "| 입력값 | 의미 |\n"
            "|--------|------|\n"
            "| `아파트` 또는 `APT` | 아파트 |\n"
            "| `오피스텔` 또는 `OPST` | 오피스텔 |\n"
            "| `원룸` 또는 `OR` | 원룸 |\n"
            "| `빌라` 또는 `VL` | 빌라/다세대주택 |\n"
            "| `다가구` 또는 `DDDGG` | 다가구주택 |\n"
            "| `주택` 또는 `HOJT` | 단독주택 |\n"
            "| `연립주택` 또는 `JWJT` | 연립주택 |"
        ),
        examples=["원룸"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "address": "서울시 마포구 합정동",
                    "netLeasableArea": 18.5,
                    "deposit": 1000,
                    "monthly": 50,
                    "type": "원룸",
                },
                {
                    "address": "대구광역시 달서구 월곡로 320",
                    "netLeasableArea": 25.0,
                    "deposit": 5000,
                    "monthly": 0,
                    "type": "아파트",
                },
            ]
        }
    }


# ──────────────────────────────────────────────
# 편의시설 스키마
# ──────────────────────────────────────────────

class FacilityItem(BaseModel):
    name: str = Field(..., description="시설명")
    lat: float = Field(..., description="위도")
    lng: float = Field(..., description="경도")


class FacilitySummary(BaseModel):
    cafes: List[FacilityItem] = Field(..., description="카페 목록 (반경 1500m)")
    convenience_stores: List[FacilityItem] = Field(..., description="편의점 목록")
    gyms: List[FacilityItem] = Field(..., description="헬스장/문화시설 목록")
    subway_stations: List[FacilityItem] = Field(..., description="지하철역 목록")
    schools: List[FacilityItem] = Field(..., description="학교 목록")
    hospitals: List[FacilityItem] = Field(..., description="병원 목록")
    banks: List[FacilityItem] = Field(..., description="은행 목록")
    parks: List[FacilityItem] = Field(..., description="공원 목록")


# ──────────────────────────────────────────────
# 매물 비교 스키마
# ──────────────────────────────────────────────

class SimilarListing(BaseModel):
    address: str = Field(..., description="매물 주소 또는 단지명")
    area: float = Field(..., description="전용면적 (㎡)")
    deposit: int = Field(..., description="보증금 (만원)")
    monthly: int = Field(..., description="월세 (만원). 매매·전세는 0")
    price: int = Field(..., description="환산가격 = 보증금 + 월세 × 10 (만원)")
    lat: float = Field(..., description="위도")
    lng: float = Field(..., description="경도")
    distance_km: float = Field(..., description="입력 매물과의 직선거리 (km)")


class ComparisonResult(BaseModel):
    cheaper_than_average: bool = Field(..., description="입력 매물이 평균보다 저렴한지 여부")
    average_price: int = Field(..., description="유사 매물 평균 환산가격 (만원)")
    average_area: float = Field(..., description="유사 매물 평균 면적 (㎡)")
    similar_listings: List[SimilarListing] = Field(..., description="수집된 유사 매물 리스트")


# ──────────────────────────────────────────────
# 기타
# ──────────────────────────────────────────────

class SummaryResponse(BaseModel):
    summary: str = Field(..., description="AI가 생성한 요약 문장")
