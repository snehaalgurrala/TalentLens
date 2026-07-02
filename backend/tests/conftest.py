import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """
    Full client with lifespan (requires DB/Redis). startup_timeout is raised
    from asgi_lifespan's 5s default because loading the local sentence-
    transformers embedding model on startup can take longer than that.
    """
    async with LifespanManager(app, startup_timeout=60, shutdown_timeout=30):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.fixture
async def client_no_lifespan():
    """Fast client that skips startup (no DB/Redis required)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
