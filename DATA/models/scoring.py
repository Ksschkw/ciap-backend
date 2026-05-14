from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from .base import Base

class InfluenceScore(Base):
    __tablename__ = 'influence_scores'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(UUID(as_uuid=True), ForeignKey('creator_profiles.id'), nullable=False)
    score = Column(Float, nullable=False)
    breakdown = Column(JSONB, nullable=True)
    model_version = Column(String, nullable=True)
    data_window_days = Column(Integer, default=30)
    platforms_included = Column(JSONB, nullable=True)
    scored_at = Column(DateTime, default=datetime.utcnow)