from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class ListingBase(BaseModel):
    brand: str
    model: str
    trim: Optional[str] = None
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    price_brl: Optional[float] = None
    final_price_brl: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    photos: List[str] = []
    url: Optional[str] = None
    seller_type: Optional[str] = None
    seller_id: Optional[int] = None
    badge: Optional[str] = None


class ListingOut(ListingBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class OpportunityResponse(BaseModel):
    items: List[ListingOut]
    count: int


class SellerStatsOut(BaseModel):
    seller_id: int
    origin: str
    reputation_medal: Optional[str] = None
    reputation_score: Optional[float] = None
    cancellations: Optional[int] = None
    response_time_hours: Optional[float] = None
    completed_sales: Optional[int] = None
    average_price_brl: Optional[float] = None
    listings_count: Optional[int] = None
    problem_rate: Optional[float] = None
    reliability_score: Optional[float] = None

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str
    preferences: Optional[Any] = None


class SearchResponse(BaseModel):
    session_id: str


class AxisBotMessage(BaseModel):
    session_id: str
    message: str


class AxisBotReply(BaseModel):
    reply: str
    listing: Optional[ListingOut]


class SellEstimateRequest(BaseModel):
    description: str
    mileage_km: Optional[int] = None
    region: Optional[str] = None


class SellEstimateResponse(BaseModel):
    min_price: float
    max_price: float
    rationale: str
