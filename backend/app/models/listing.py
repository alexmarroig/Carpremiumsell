import datetime as dt
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class SearchProfile(Base):
    __tablename__ = "search_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    preferences = Column(JSON, nullable=False)
    region = Column(String, nullable=False)


class ListingSource(Base):
    __tablename__ = "listing_sources"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)


class RawListing(Base):
    __tablename__ = "raw_listings"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("listing_sources.id"), nullable=False)
    external_id = Column(String, nullable=False)
    raw_payload = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    source = relationship("ListingSource")


class NormalizedListing(Base):
    __tablename__ = "normalized_listings"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("listing_sources.id"), nullable=False)
    external_id = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    trim = Column(String)
    year = Column(Integer)
    mileage_km = Column(Integer)
    price_brl = Column(Float)
    supplier_price_brl = Column(Float)
    final_price_brl = Column(Float)
    city = Column(String)
    state = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    photos = Column(JSON, default=list)
    url = Column(String)
    seller_type = Column(String)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    status = Column(String, default="active")
    trust_badge = Column(String)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    source = relationship("ListingSource")
    seller = relationship("Seller", back_populates="listings")


class MarketStats(Base):
    __tablename__ = "market_stats"

    id = Column(Integer, primary_key=True)
    region_key = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    trim = Column(String)
    year_range = Column(String)
    median_price = Column(Float)
    p25 = Column(Float)
    p75 = Column(Float)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query_text = Column(String, nullable=False)
    chosen_listing_id = Column(Integer, ForeignKey("normalized_listings.id"))
    rationale_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    listing = relationship("NormalizedListing")


class Seller(Base):
    __tablename__ = "sellers"
    __table_args__ = (UniqueConstraint("origin", "external_id", name="uq_seller_origin_external"),)

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("listing_sources.id"), nullable=True)
    origin = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    reputation_medal = Column(String)
    reputation_score = Column(Float)
    cancellations = Column(Integer)
    response_time_hours = Column(Float)
    completed_sales = Column(Integer)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    listings = relationship("NormalizedListing", back_populates="seller")


class SellerStats(Base):
    __tablename__ = "seller_stats"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False, unique=True)
    average_price_brl = Column(Float)
    listings_count = Column(Integer)
    completed_sales = Column(Integer)
    problem_rate = Column(Float)
    reliability_score = Column(Float)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    seller = relationship("Seller")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_json = Column(JSON, nullable=False)
    region_key = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
