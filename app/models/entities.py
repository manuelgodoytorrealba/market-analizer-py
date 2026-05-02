from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_listings_source_external_id"),
        Index("ix_listings_source_active", "source", "is_active"),
        Index("ix_listings_normalized_name", "normalized_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)  # wallapop, ebay, etc
    external_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    normalized_name = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, nullable=True)
    url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    seller_location = Column(String, nullable=True)
    shipping_region = Column(String, nullable=True)
    search_query = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    shipping_cost = Column(Float, nullable=True)
    buy_it_now = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (Index("ix_opportunities_score", "score"),)

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    source = Column(String, nullable=False)
    listing_id = Column(Integer, nullable=True)
    source_listing_id = Column(Integer, nullable=True)
    normalized_name = Column(String, nullable=True)
    search_query = Column(String, nullable=True)
    opportunity_type = Column(String, nullable=True)
    buy_it_now = Column(Boolean, default=True)
    buy_price = Column(Float, nullable=False)
    estimated_resale_price = Column(Float, nullable=True)
    profit_estimate = Column(Float, nullable=True)
    fees_estimate = Column(Float, nullable=True)
    shipping_estimate = Column(Float, nullable=True)
    liquidity_count = Column(Integer, nullable=True)
    manual_decision = Column(String, nullable=True)
    estimated_sale_price = Column(Float, nullable=False)
    expected_profit = Column(Float, nullable=False)
    discount_pct = Column(Float, nullable=True)
    comparable_count = Column(Integer, nullable=True)
    confidence = Column(String, nullable=True)
    metric_name = Column(String, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)
    score = Column(Float, nullable=False)
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    __table_args__ = (
        Index("ix_scrape_runs_started_at", "started_at"),
        Index("ix_scrape_runs_source", "source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False)
    query_count = Column(Integer, nullable=False, default=0)
    queries_json = Column(Text, nullable=True)
    listings_seen = Column(Integer, nullable=False, default=0)
    listings_normalized = Column(Integer, nullable=False, default=0)
    inserted = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    deactivated = Column(Integer, nullable=False, default=0)
    opportunities_generated = Column(Integer, nullable=False, default=0)
    errors_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    summary_json = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, default=datetime.utcnow)
