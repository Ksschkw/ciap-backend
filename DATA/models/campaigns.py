from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sme_id = Column(UUID(as_uuid=True), ForeignKey('sme_profiles.id'), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String, nullable=True)
    objective = Column(String, nullable=False)
    total_budget_ngn = Column(Numeric, nullable=True)
    spent_budget_ngn = Column(Numeric, default=0.0)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    target_platforms = Column(JSONB, nullable=True)
    target_categories = Column(JSONB, nullable=True)
    target_locations = Column(JSONB, nullable=True)
    min_influence_score = Column(Float, nullable=True)
    min_followers = Column(Integer, nullable=True)
    status = Column(String, default="DRAFT", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collaborations = relationship("CampaignCollaboration", back_populates="campaign")


class CampaignCollaboration(Base):
    __tablename__ = 'campaign_collaborations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.id'), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('creator_profiles.id'), nullable=False)
    content_id = Column(UUID(as_uuid=True), ForeignKey('content_items.id'), nullable=True)
    negotiated_fee_ngn = Column(Numeric, nullable=True)
    payment_gateway_reference = Column(String, nullable=True)
    tracking_link = Column(String, nullable=True)
    tracking_code = Column(String, unique=True, index=True, nullable=True)
    total_clicks = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    estimated_roi = Column(Float, nullable=True)
    status = Column(String, default="INVITED", index=True)
    
    invited_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="collaborations")
    content_item = relationship("ContentItem", back_populates="campaign_collaborations")
    brief = relationship("CampaignCreatorBrief", back_populates="collaboration", uselist=False)
    conversion_events = relationship("ConversionEvent", back_populates="collaboration")


class CampaignCreatorBrief(Base):
    __tablename__ = 'campaign_creator_briefs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaboration_id = Column(UUID(as_uuid=True), ForeignKey('campaign_collaborations.id'), unique=True, nullable=False)
    deliverables = Column(String, nullable=False)
    dos = Column(JSONB, nullable=True)
    donts = Column(JSONB, nullable=True)
    brand_keywords = Column(JSONB, nullable=True)
    hashtags_required = Column(JSONB, nullable=True)
    reference_links = Column(JSONB, nullable=True)
    submission_deadline = Column(Date, nullable=True)
    revision_limit = Column(Integer, default=2)
    additional_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collaboration = relationship("CampaignCollaboration", back_populates="brief")


class ConversionEvent(Base):
    __tablename__ = 'conversion_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaboration_id = Column(UUID(as_uuid=True), ForeignKey('campaign_collaborations.id'), nullable=False)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow)
    tracking_code = Column(String, nullable=False, index=True)
    revenue_ngn = Column(Numeric, nullable=True)
    session_id = Column(String, nullable=True)
    ip_country = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    custom_data = Column(JSONB, nullable=True)

    # Relationships
    collaboration = relationship("CampaignCollaboration", back_populates="conversion_events")