import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_root_returns_project_info(client_no_lifespan: AsyncClient) -> None:
    response = await client_no_lifespan.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["project"] == settings.PROJECT_NAME
    assert body["version"] == settings.VERSION


@pytest.mark.asyncio
async def test_health_shape_without_services(client_no_lifespan: AsyncClient) -> None:
    response = await client_no_lifespan.get("/health")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "services" in body
    assert "database" in body["services"]
    assert "redis" in body["services"]


@pytest.mark.asyncio
async def test_openapi_schema_available(client_no_lifespan: AsyncClient) -> None:
    response = await client_no_lifespan.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == settings.PROJECT_NAME
