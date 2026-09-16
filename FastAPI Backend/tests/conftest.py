# Test configuration for CA Nexus Backend

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.database import Base
from app.core.database.session import AsyncSessionLocal, get_async_db, get_tenant_db
from app.core.tenancy.context import TenantContext, get_tenant_context, set_tenant_context
from app.main import app
import app.models  # Import all models to register with SQLAlchemy
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.core.security import hash_password

# Test database URL - uses a separate test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ca_nexus:ca_nexus_dev_password@localhost:5432/ca_nexus_test"
)

# Override settings for testing
class TestSettings(Settings):
    ENVIRONMENT: str = "testing"
    DEBUG: bool = True
    DATABASE_URL: str = TEST_DATABASE_URL
    REDIS_URL: str = "redis://localhost:6379/3"  # Different DB for tests
    CELERY_BROKER_URL: str = "redis://localhost:6379/4"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/5"
    SECRET_KEY: str = "test-secret-key-for-testing-only-minimum-32-chars-long"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = "dGVzdC1lbmNyeXB0aW9uLWtleS10aGlydHktdHdvLWJ5dGVzLQ=="  # base64 encoded 32 bytes


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Note: alembic migrations are assumed to be already applied to the test database.
    # For CI, run `alembic upgrade head` as a separate step before tests.
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    
    async with async_session() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()


@pytest.fixture(scope="function")
async def tenant_db_session(db_session) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session with tenant context set."""
    # Create a test tenant
    tenant_id = uuid.uuid4()
    firm = Firm(
        id=tenant_id,
        name="Test Firm",
        display_name="Test Firm",
        is_active=True,
        settings={},
        country="India",
    )
    db_session.add(firm)
    await db_session.flush()
    
    # Set tenant context
    context = TenantContext(tenant_id=tenant_id, firm=firm, user_id=None)
    set_tenant_context(context)
    
    # Set tenant context on session
    await db_session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
    
    try:
        yield db_session
    finally:
        # Clean up tenant context
        from app.core.tenancy.context import clear_tenant_context
        clear_tenant_context()


@pytest.fixture(scope="function")
async def test_firm(db_session) -> Firm:
    """Create a test firm."""
    firm = Firm(
        name="Test Firm",
        display_name="Test Firm",
        registration_number="TEST123",
        is_active=True,
        settings={},
        country="India",
    )
    db_session.add(firm)
    await db_session.flush()
    await db_session.refresh(firm)
    return firm


@pytest.fixture(scope="function")
async def test_user(db_session, test_firm) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test User",
        tenant_id=test_firm.id,
        roles=["associate"],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def admin_user(db_session, test_firm) -> User:
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        tenant_id=test_firm.id,
        roles=["firm_admin"],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def override_get_async_db(db_session):
    """Override the get_async_db dependency for testing."""
    async def _override_get_async_db():
        yield db_session
    
    app.dependency_overrides[get_async_db] = _override_get_async_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_get_tenant_db(tenant_db_session):
    """Override the get_tenant_db dependency for testing."""
    async def _override_get_tenant_db():
        yield tenant_db_session
    
    app.dependency_overrides[get_tenant_db] = _override_get_tenant_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.scan = AsyncMock(return_value=(0, []))
    return mock


@pytest.fixture
def override_get_redis(mock_redis):
    """Override get_redis dependency."""
    from app.core.redis.client import get_redis
    
    async def _override_get_redis():
        return mock_redis
    
    app.dependency_overrides[get_redis] = _override_get_redis
    yield
    app.dependency_overrides.clear()


# Test data factories
class TestDataFactory:
    @staticmethod
    def create_firm_data(**overrides) -> dict[str, Any]:
        data = {
            "name": "Test Firm",
            "display_name": "Test Firm",
            "registration_number": "TEST123",
            "is_active": True,
            "settings": {},
            "country": "India",
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_user_data(**overrides) -> dict[str, Any]:
        data = {
            "email": "test@example.com",
            "password": "TestPass123!",
            "full_name": "Test User",
            "roles": ["associate"],
            "is_active": True,
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_client_data(**overrides) -> dict[str, Any]:
        data = {
            "name": "Test Client",
            "category": "COMPANY",
            "status": "ACTIVE",
            "address": "123 Test St",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
        }
        data.update(overrides)
        return data


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    return TestDataFactory()


# Async test client
@pytest.fixture
async def async_client():
    from httpx import AsyncClient, ASGITransport
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "db: Tests requiring database")


# Custom assertions
def assert_response_success(response, status_code=200):
    assert response.status_code == status_code, f"Expected {status_code}, got {response.status_code}: {response.text}"


def assert_response_error(response, status_code=400):
    assert response.status_code == status_code, f"Expected {status_code}, got {response.status_code}: {response.text}"
    data = response.json()
    assert "detail" in data or "errors" in data


def assert_paginated_response(response, expected_keys=None):
    assert_response_success(response)
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    if expected_keys:
        for item in data["items"]:
            for key in expected_keys:
                assert key in item, f"Missing key {key} in item"


def assert_error_response(response, expected_code=None):
    assert response.status_code >= 400
    data = response.json()
    if expected_code:
        assert data.get("code") == expected_code or str(response.status_code) == str(expected_code)
    return data