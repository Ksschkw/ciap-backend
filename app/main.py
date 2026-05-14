import asyncio
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings



if sys.platform != "win32":
    try:
        import uvloop
    except ImportError:
        uvloop = None
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React dev server
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router, prefix=settings.api_v1_prefix)


from fastapi.responses import RedirectResponse
from DATA.core.database import SessionLocal
from sqlalchemy import text

@app.get("/", include_in_schema=False)
def read_root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Empty response for favicon requests."""
    return {}


@app.get("/health", tags=["system"], summary="Platform Health Check", response_description="System status including DB connection")
def health_check() -> dict[str, str]:
    """
    Perform a robust system health check.
    
    Verifies that the application server is running and that the PostgreSQL 
    database is reachable. This endpoint is safe to call frequently by load balancers.
    """
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
        
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": "1.0.0"
    }
