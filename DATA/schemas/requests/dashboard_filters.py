"""
Request models for creator dashboard API endpoints.

These Pydantic classes validate query parameters and JSON bodies
sent by the Frontend when fetching dashboard data.

Classes:
    DateRangeFilter     - date range + preset shortcuts
    PaginationParams    - limit/offset with sensible defaults
    DashboardFilters    - platform filter + date range for dashboard queries
    ContentListRequest  - paginated content list with filters
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DatePreset(str, enum.Enum):
    """Shortcut presets so the frontend doesn't have to compute date ranges."""
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_90_DAYS = "LAST_90_DAYS"
    LAST_6_MONTHS = "LAST_6_MONTHS"
    LAST_12_MONTHS = "LAST_12_MONTHS"
    CUSTOM = "CUSTOM"   # Must provide from_date and to_date


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


# ---------------------------------------------------------------------------
# PaginationParams
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    """Standard pagination for any list endpoint."""
    limit: int = Field(default=20, ge=1, le=100, description="Items per page.")
    offset: int = Field(default=0, ge=0, description="Number of items to skip.")


# ---------------------------------------------------------------------------
# DateRangeFilter
# ---------------------------------------------------------------------------

class DateRangeFilter(BaseModel):
    """
    Flexible date range filter supporting both presets and custom ranges.
    The Backend resolves presets into from_date/to_date before querying.
    """
    preset: DatePreset = Field(
        default=DatePreset.LAST_30_DAYS,
        description="Shortcut. Frontend should default to LAST_30_DAYS.",
    )
    from_date: Optional[date] = Field(
        None, description="Required when preset=CUSTOM. Format: YYYY-MM-DD."
    )
    to_date: Optional[date] = Field(
        None, description="Required when preset=CUSTOM. Format: YYYY-MM-DD."
    )

    @model_validator(mode="after")
    def validate_custom_range(self) -> "DateRangeFilter":
        if self.preset == DatePreset.CUSTOM:
            if not self.from_date or not self.to_date:
                raise ValueError("from_date and to_date are required when preset is CUSTOM.")
            if self.from_date > self.to_date:
                raise ValueError("from_date must be before to_date.")
        return self


# ---------------------------------------------------------------------------
# DashboardFilters
# ---------------------------------------------------------------------------

class DashboardFilters(BaseModel):
    """
    Combined filter for Creator Dashboard API.
    All filters are optional — omitting any returns all data.
    """
    date_range: DateRangeFilter = Field(
        default_factory=lambda: DateRangeFilter(from_date=None, to_date=None)
    )
    platforms: Optional[List[str]] = Field(
        None,
        description="Filter to specific platforms only, e.g. ['YOUTUBE', 'INSTAGRAM']. "
                    "NULL = all connected platforms.",
    )


# ---------------------------------------------------------------------------
# ContentListRequest
# ---------------------------------------------------------------------------

class ContentSortField(str, enum.Enum):
    POSTED_AT = "posted_at"
    VIEWS = "views"
    LIKES = "likes"
    ENGAGEMENT_RATE = "engagement_rate"
    COMMENTS = "comments"
    SHARES = "shares"


class ContentListRequest(BaseModel):
    """
    Paginated, filterable, sortable request for a creator's content list.
    Used by the 'My Content' section of the Creator Dashboard.
    """
    pagination: PaginationParams = Field(default_factory=lambda: PaginationParams())
    date_range: DateRangeFilter = Field(
        default_factory=lambda: DateRangeFilter(from_date=None, to_date=None)
    )
    platforms: Optional[List[str]] = Field(None)
    media_types: Optional[List[str]] = Field(
        None, description="Filter by media type, e.g. ['VIDEO', 'REEL']."
    )
    sort_by: ContentSortField = Field(default=ContentSortField.POSTED_AT)
    sort_order: SortOrder = Field(default=SortOrder.DESC)
    search_query: Optional[str] = Field(
        None, max_length=200, description="Full-text search on caption/title."
    )