from pydantic import BaseModel
from typing import List

# 요청 스키마
class HousingRequest(BaseModel):
    address: str
    netLeasableArea: float  # 평 단위 입력
    deposit: int            # 만원 단위 보증금
    monthly: int            # 만원 단위 월세

# 편의시설 아이템 (이름 + 위치)
class FacilityItem(BaseModel):
    name: str
    lat: float
    lng: float

# 편의시설 요약 (각 카테고리 별 리스트)
class FacilitySummary(BaseModel):
    cafes: list[FacilityItem]
    convenience_stores: list[FacilityItem]
    gyms: list[FacilityItem]
    subway_stations: list[FacilityItem]
    schools: list[FacilityItem]
    hospitals: list[FacilityItem]
    banks: list[FacilityItem]
    parks: list[FacilityItem]
    # bus_stops: list[FacilityItem]

# 유사 매물 정보
class SimilarListing(BaseModel):
    address: str
    area: float               # ㎡ 기준
    deposit: int              # 만원
    monthly: int              # 만원
    price: int                # 계산된 보증금 + 월세 * 10
    lat: float
    lng: float
    distance_km: float        # 현재 매물과의 거리

# 비교 결과
class ComparisonResult(BaseModel):
    cheaper_than_average: bool
    average_price: int
    average_area: float
    similar_listings: List[SimilarListing]

# AI 요약 응답만 필요할 때
class SummaryResponse(BaseModel):
    summary: str
