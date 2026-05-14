from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_analytics_service
from app.dependencies import get_creator_service
from app.dependencies import get_current_user
from app.main import app


TEST_USER_ID = UUID("2f2ab7c8-7e9f-4d81-8f6d-6d8d8d2f2b3a")


async def override_current_user() -> dict[str, str]:
    return {"id": str(TEST_USER_ID), "email": "creator@example.com", "role": "CREATOR"}


class FakeCreatorService:
    async def get_dashboard(self, creator_id: UUID) -> dict[str, object]:
        assert creator_id == TEST_USER_ID
        return {
            "creator": {
                "id": str(creator_id),
                "full_name": "Amina Yusuf",
                "category": "Lifestyle",
                "language_preference": "en",
                "influence_score": 82.4,
                "is_public": True,
            },
            "summary": {
                "followers": 120000,
                "total_views": 3400000,
                "engagement_rate": 0.078,
                "growth_rate": 0.114,
                "influence_score": 82.4,
            },
            "platform_breakdown": [],
            "top_content": [],
            "trend": []
        }


class FakeAnalyticsService:
    async def summary(self, creator_id: UUID) -> dict[str, object]:
        assert creator_id == TEST_USER_ID
        return {
            "followers": 120000,
            "views": 3400000,
            "engagement_rate": 0.078,
            "growth_rate": 0.114,
            "content_count": 87,
        }


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_creator_service] = FakeCreatorService
    app.dependency_overrides[get_analytics_service] = FakeAnalyticsService

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_creator_dashboard_smoke(client: TestClient) -> None:
    response = client.get("/api/v1/creator/dashboard")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()
    assert body["creator"]["id"] == str(TEST_USER_ID)
    assert body["summary"]["followers"] == 120000


def test_analytics_summary_smoke(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()
    assert body["followers"] == 120000
    assert body["content_count"] == 87