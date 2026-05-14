# CIAP Backend Architecture & Setup Guide

## System Overview

The Creative Influence Analytics Platform (CIAP) backend is a RESTful API service built to aggregate, normalize, and score cross-platform creator metrics. The initial MVP focuses on YouTube Data API v3 and YouTube Analytics API integrations, processing engagement, reach, and demographic data to generate heuristic-based influence scores for content creators. The system surfaces this data to SMEs (Subject Matter Experts/Agencies- Small Medium size Enterprises) for creator discovery and campaign planning.

## Technology Stack

*   **Language:** Python 3.10+
*   **Web Framework:** FastAPI
*   **Database:** PostgreSQL 15+
*   **ORM:** SQLAlchemy 2.0
*   **Migrations:** Alembic
*   **Authentication:** JWT (JSON Web Tokens) with HttpOnly cookies
*   **External APIs (for now):** Google OAuth 2.0, YouTube Data API v3, YouTube Analytics API
*   **Task Queue (Optional):** Celery with Redis broker

## Architecture & Data Flow

### Authentication & Authorization
The platform utilizes dual-layered identification:
1.  **User Identity (`user_id`):** Primary key in the `users` table. Used for authentication, JWT sub-claims, and role-based access control (RBAC).
2.  **Creator Identity (`creator_profile_id`):** Primary key in the `creator_profiles` table, linked via foreign key to `users`. Used for data aggregation, scoring, and public discovery.

The authentication flow utilizes secure, HttpOnly cookies (`access_token` and `refresh_token`) set via the `POST /api/v1/auth/login` endpoint. Subsequent client requests must include credentials to authenticate seamlessly.

### Data Ingestion Engine
Data ingestion is triggered explicitly via `POST /api/v1/youtube/sync`.
1.  **OAuth Token Management:** The system retrieves the creator's stored `access_token` and `refresh_token`. If the access token is expired, it automatically requests a new token from the Google OAuth server and persists the updated token.
2.  **Data Extraction:** The system queries YouTube for video metadata, historical performance metrics (views, likes, comments), and private channel demographics (age distribution, geographic audience).
3.  **Data Normalization:** Raw JSON payloads are normalized into relational records (`ContentItem`, `ContentMetricSnapshot`, `AudienceSnapshot`).

### Influence Scoring
The scoring module (`InfluenceScorer`) computes a normalized influence score (0-100) based on three primary vectors:
1.  **Engagement Component:** Normalizes (Likes + Comments) / Reach.
2.  **Growth Component:** Evaluates subscriber and viewership velocity.
3.  **Audience Quality:** Evaluates demographic concentration.

Creators are subsequently bucketed into tiers (Nano, Micro, Mid-Tier, Macro, Mega) for simplified SME filtering.

## Setup Instructions

### 1. Repository Setup
```bash
git clone https://github.com/30Cycleltd/ciap-mvp-a.git
cd ciap-mvp-a/ciap-backend
```

### 2. Environment Configuration
Create a virtual environment and install dependencies from the provided requirements specification.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root `ciap-backend` directory:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/ciap_db
SECRET_KEY=your_secure_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google API Credentials
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/v1/oauth/youtube/callback

ENVIRONMENT=development
```

### 4. Database Initialization
Ensure PostgreSQL is running and execute the schema migrations:
```bash
alembic upgrade head
```

### 5. Application Execution
Start the ASGI server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. 
OpenAPI documentation is auto-generated and accessible at `http://127.0.0.1:8000/docs`.
