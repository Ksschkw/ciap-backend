"""
YouTube Endpoints
=================
Two endpoints that implement the DB-first YouTube strategy:

POST /api/v1/youtube/ingest-public
    - Admin/system call to populate DB with public creator data from YouTube
    - SMEs NEVER call YouTube directly; they search our DB via /discover/creators

POST /api/v1/youtube/sync
    - Authenticated creator syncs their own channel stats into our DB
    - Updates their Creator Dashboard (content metrics, audience snapshots)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from DATA.core.database import get_db
from app.dependencies import get_current_user
from app.services.youtube_ingestion import ingest_public_creators, sync_creator_youtube_channel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.post("/ingest-public")
def ingest_youtube_creators(
    query: str = Query(default="Nigerian creator", description="Search term to find creators on YouTube"),
    max_results: int = Query(default=25, ge=1, le=50, description="Max channels to ingest per call"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """
    **Admin / background job endpoint.**

    Searches YouTube for public creators matching `query`, fetches their channel
    stats and latest 5 videos, then stores everything into our database.

    After calling this, SMEs can discover these creators via `GET /discover/creators`
    without ever touching the YouTube API — protecting my quota lol.

    **No authentication required for MVP** (add role guard before going to production).
    """
    result = ingest_public_creators(db, query=query, max_results=max_results)
    return {
        "success": True,
        "message": f"Ingested {result['ingested']} YouTube channel(s) into the database.",
        "data": result,
    }


@router.post("/sync")
def sync_my_youtube_channel(
    current_user: dict[str, str] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """
    **Creator endpoint.**

    A logged-in creator triggers a sync of their connected YouTube channel.
    Pulls latest video stats and audience data from YouTube and stores them
    in our database, powering their Creator Dashboard.

    Requires: Bearer token (Creator must be logged in).
    """
    user_id = UUID(current_user["id"])
    result = sync_creator_youtube_channel(db, user_id=user_id)
    return result
