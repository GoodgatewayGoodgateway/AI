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


# ──────────────────────────────────────────────
# 시세 통계 스키마
# ──────────────────────────────────────────────

class MarketTypeStats(BaseModel):
    count: int = Field(..., description="매물 수")
    avg_price: int = Field(..., description="평균 환산가격 (만원)")
    avg_area_m2: float = Field(..., description="평균 면적 (㎡)")


class MarketStatsResponse(BaseModel):
    area: str = Field(..., description="조회 지역명")
    total_count: int = Field(..., description="전체 매물 수")
    by_type: dict = Field(..., description="타입별 통계")
    price_range: dict = Field(..., description="최저·최고 환산가격 (만원)")


# ──────────────────────────────────────────────
# 매물 점수 스키마
# ──────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    price_score: int = Field(..., description="가격 점수 (0~100). 시세 대비 저렴할수록 높음")
    facilities_score: int = Field(..., description="편의시설 점수 (0~100). 주변 시설 수 기반")
    transit_score: int = Field(..., description="교통 점수 (0~100). 지하철역 수 기반")


class ScoreResponse(BaseModel):
    total_score: int = Field(..., description="종합 점수 (0~100)")
    breakdown: ScoreBreakdown
    grade: str = Field(..., description="등급 (S / A / B / C / D / F)")


# ──────────────────────────────────────────────
# 추천 매물 스키마
# ──────────────────────────────────────────────

class RecommendRequest(BaseModel):
    query: str = Field(..., description="지역명 또는 주소. 예) 강남구, 홍대입구역", examples=["마포구"])
    max_deposit: Optional[int] = Field(None, description="최대 보증금 (만원)", examples=[5000])
    max_monthly: Optional[int] = Field(None, description="최대 월세 (만원)", examples=[60])
    min_area_pyeong: Optional[float] = Field(None, description="최소 면적 (평)", examples=[5.0])
    preferred_types: Optional[List[str]] = Field(None, description="선호 유형 목록. 예) ['원룸', '빌라']", examples=[["원룸"]])
    top_n: int = Field(5, description="추천 매물 수 (기본 5, 최대 20)", ge=1, le=20)


# ──────────────────────────────────────────────
# 즐겨찾기 스키마
# ──────────────────────────────────────────────

class FavoriteRequest(BaseModel):
    user_id: str = Field(..., description="사용자 식별자 (앱에서 관리)", examples=["user_abc123"])
    listing_id: int = Field(..., description="즐겨찾기할 매물 ID", examples=[42])


# ──────────────────────────────────────────────
# 가격 트렌드 스키마
# ──────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    avg_price: int = Field(..., description="평균 환산가격 (만원)")
    count: int = Field(..., description="해당 날짜 매물 수")


class TrendResponse(BaseModel):
    area: str = Field(..., description="조회 지역명")
    type: Optional[str] = Field(None, description="매물 유형 필터 (없으면 전체)")
    trend: List[TrendPoint] = Field(..., description="날짜별 평균 가격 추이")
