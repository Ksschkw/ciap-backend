from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class ContentItem(Base):
    __tablename__ = 'content_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('creator_profiles.id'), nullable=False)
    platform_connection_id = Column(UUID(as_uuid=True), ForeignKey('platform_connections.id'), nullable=False)
    platform = Column(String, nullable=False)
    external_id = Column(String, nullable=False, unique=True, index=True)
    media_type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    caption = Column(String, nullable=True)
    hashtags = Column(JSONB, nullable=True)
    permalink = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String, default="ACTIVE")
    detected_language = Column(String, nullable=True)
    posted_at = Column(DateTime, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("CreatorProfile", back_populates="content_items")
    platform_connection = relationship("PlatformConnection", back_populates="content_items")
    metric_snapshots = relationship("ContentMetricSnapshot", back_populates="content_item")
    campaign_collaborations = relationship("CampaignCollaboration", back_populates="content_item")


class ContentMetricSnapshot(Base):
    __tablename__ = 'content_metric_snapshots'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    views = Column(BigInteger, nullable=True)
    likes = Column(BigInteger, nullable=True)
    comments = Column(BigInteger, nullable=True)
    shares = Column(BigInteger, nullable=True)
    saves = Column(BigInteger, nullable=True)
    reposts = Column(BigInteger, nullable=True)
    watch_time_seconds = Column(Integer, nullable=True)
    average_view_duration_seconds = Column(Integer, nullable=True)
    click_through_rate = Column(Float, nullable=True)
    streams = Column(BigInteger, nullable=True)
    playlist_adds = Column(BigInteger, nullable=True)
    impressions = Column(BigInteger, nullable=True)
    reach = Column(BigInteger, nullable=True)
    engagement_rate = Column(Float, nullable=True)

    # Relationships
    content_item = relationship("ContentItem", back_populates="metric_snapshots")


class AudienceSnapshot(Base):
    __tablename__ = 'audience_snapshots'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform_connection_id = Column(UUID(as_uuid=True), ForeignKey('platform_connections.id'), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('creator_profiles.id'), nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    total_followers = Column(Integer, nullable=True)
    new_followers_this_period = Column(Integer, nullable=True)
    age_distribution = Column(JSONB, nullable=True)
    gender_distribution = Column(JSONB, nullable=True)
    top_countries = Column(JSONB, nullable=True)
    top_cities = Column(JSONB, nullable=True)
    top_languages = Column(JSONB, nullable=True)

    # Relationships
    platform_connection = relationship("PlatformConnection", back_populates="audience_snapshots")
    creator = relationship("CreatorProfile", back_populates="audience_snapshots")