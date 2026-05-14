from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    role = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    language_preference = Column(String, default="en")
    status = Column(String, default="PENDING_VERIFICATION", index=True)
    subscription_plan = Column(String, default="FREE")
    is_email_verified = Column(Boolean, default=False)
    is_merged = Column(Boolean, default=False, index=True)
    merged_into_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator_profile = relationship("CreatorProfile", back_populates="user", uselist=False)
    sme_profile = relationship("SMEProfile", back_populates="user", uselist=False)
    platform_connections = relationship("PlatformConnection", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class CreatorProfile(Base):
    __tablename__ = 'creator_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True, nullable=False)
    category = Column(String, nullable=False, index=True)
    secondary_categories = Column(JSONB, nullable=True)
    bio = Column(String, nullable=True)
    location_country = Column(String(2), nullable=True)
    location_city = Column(String, nullable=True)
    social_handles = Column(JSONB, nullable=True)
    influence_score = Column(Float, nullable=True)
    total_followers = Column(Integer, nullable=True)
    avg_engagement_rate = Column(Float, nullable=True)
    is_public = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="creator_profile")
    content_items = relationship("ContentItem", back_populates="creator")
    audience_snapshots = relationship("AudienceSnapshot", back_populates="creator")


class SMEProfile(Base):
    __tablename__ = 'sme_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    industry = Column(String, nullable=False, index=True)
    website_url = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    description = Column(String, nullable=True)
    payment_gateway_customer_id = Column(String, nullable=True)
    monthly_budget_ngn = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sme_profile")


class PlatformConnection(Base):
    __tablename__ = 'platform_connections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    platform_name = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    platform_user_id = Column(String, nullable=False)
    platform_username = Column(String, nullable=True)
    scopes_granted = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="platform_connections")
    content_items = relationship("ContentItem", back_populates="platform_connection")
    audience_snapshots = relationship("AudienceSnapshot", back_populates="platform_connection")


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    action_url = Column(String, nullable=True)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")