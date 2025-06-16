from pydantic import BaseModel
from typing import List

class HousingRequest(BaseModel):
    address: str
    area: float
    price: int

class FacilitySummary(BaseModel):
    cafes: int
    gyms: int
    convenience_stores: int

class SimilarListing(BaseModel):
    address: str
    area: float
    price: int
    lat: float
    lng: float

class ComparisonResult(BaseModel):
    cheaper_than_average: bool
    average_price: int
    average_area: float
    similar_listings: list[SimilarListing]

class SummaryResponse(BaseModel):
    summary: str

class FacilityItem(BaseModel):
    name: str
    lat: float
    lng: float

class FacilitySummary(BaseModel):
    cafes: list[FacilityItem]
    gyms: list[FacilityItem]
    convenience_stores: list[FacilityItem]

