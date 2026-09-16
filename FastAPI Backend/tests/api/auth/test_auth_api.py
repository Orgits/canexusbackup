# Auth API Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schemas import LoginRequest, RefreshRequest
from app.modules.users.models import User
from app.modules.firms.models import Firm
from app.core.security import hash_password


class TestAuthAPI:
    """Integration tests for auth endpoints."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(
            name="Test Firm",
            display_name="Test Firm",
            is_active=True,
            settings={},
            country="India",
        )
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
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

    @pytest.mark.api
    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.api
    async def test_login_invalid_credentials(self, async_client: AsyncClient, test_user: User):
        """Test login with invalid password."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "WrongPass123!"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.api
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "TestPass123!"}
        )
        assert response.status_code == 401

    @pytest.mark.api
    async def test_login_invalid_email_format(self, async_client: AsyncClient):
        """Test login with invalid email format."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "not-an-email", "password": "TestPass123!"}
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.api
    async def test_login_short_password(self, async_client: AsyncClient):
        """Test login with password too short (validation)."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "short"}
        )
        # Password validation happens in service, not schema
        assert response.status_code in (401, 422)

    @pytest.mark.api
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should be different
        assert data["refresh_token"] != refresh_token

    @pytest.mark.api
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )
        assert response.status_code == 401

    @pytest.mark.api
    async def test_refresh_token_reuse_detection(self, async_client: AsyncClient, test_user: User):
        """Test that reusing a refresh token is rejected."""
        # Login to get tokens
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # First refresh - should succeed
        response1 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response1.status_code == 200
        new_refresh_token = response1.json()["refresh_token"]

        # Second refresh with SAME old token - should fail
        response2 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response2.status_code == 401

        # But new token should work
        response3 = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": new_refresh_token}
        )
        assert response3.status_code == 200

    @pytest.mark.api
    async def test_logout_success(self, async_client: AsyncClient, test_user: User):
        """Test successful logout."""
        # Login first
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        access_token = login_response.json()["access_token"]

        # Logout
        response = await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 204

    @pytest.mark.api
    async def test_logout_revokes_access_token(self, async_client: AsyncClient, test_user: User):
        """Test that logout revokes the access token."""
        # Login first
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        access_token = login_response.json()["access_token"]

        # Verify token works
        me_response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200

        # Logout
        await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Token should now be revoked
        me_response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 401

    @pytest.mark.api
    async def test_logout_invalidates_refresh_tokens(self, async_client: AsyncClient, test_user: User):
        """Test that logout invalidates all refresh tokens."""
        # Login first
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        access_token = login_response.json()["access_token"]
        await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Refresh token should now be invalid
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 401

    @pytest.mark.api
    async def test_me_endpoint(self, async_client: AsyncClient, test_user: User):
        """Test /me endpoint."""
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        access_token = login_response.json()["access_token"]

        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "roles" in data
        assert "permissions" in data
        assert "tenant_id" in data

    @pytest.mark.api
    async def test_me_unauthorized(self, async_client: AsyncClient):
        """Test /me endpoint without token."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.api
    async def test_me_invalid_token(self, async_client: AsyncClient):
        """Test /me endpoint with invalid token."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401


class TestAuthAPIPasswordManagement:
    """Tests for password management endpoints."""

    @pytest_asyncio.fixture
    async def auth_headers(self, async_client: AsyncClient, test_user: User) -> dict:
        """Get auth headers for test user."""
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        access_token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.mark.api
    async def test_change_password_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful password change."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewValidPass123!"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.api
    async def test_change_password_wrong_current(self, async_client: AsyncClient, auth_headers: dict):
        """Test password change with wrong current password."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPass123!",
                "new_password": "NewValidPass123!"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "Current password is incorrect" in str(data)

    @pytest.mark.api
    async def test_change_password_same_as_current(self, async_client: AsyncClient, auth_headers: dict):
        """Test password change with same password."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "TestPass123!"
            },
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.api
    async def test_change_password_invalid_new(self, async_client: AsyncClient, auth_headers: dict):
        """Test password change with invalid new password."""
        response = await async_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "weak"
            },
            headers=auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.api
    async def test_reset_password_success(self, async_client: AsyncClient):
        """Test admin password reset."""
        response = await async_client.post(
            "/api/auth/reset-password",
            json={
                "email": "test@example.com",
                "new_password": "NewValidPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.api
    async def test_reset_password_user_not_found(self, async_client: AsyncClient):
        """Test admin password reset for non-existent user."""
        response = await async_client.post(
            "/api/auth/reset-password",
            json={
                "email": "nonexistent@example.com",
                "new_password": "NewValidPass123!"
            }
        )
        assert response.status_code == 400


class TestAuthAPILockout:
    """Tests for account lockout functionality."""

    @pytest.mark.api
    async def test_account_lockout_after_failed_attempts(self, async_client: AsyncClient, test_user: User):
        """Test account lockout after 5 failed attempts."""
        for i in range(5):
            response = await async_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": f"WrongPass{i}!"}
            )
            assert response.status_code == 401

        # 6th attempt should be locked
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "WrongPass6!"}
        )
        assert response.status_code == 403
        data = response.json()
        assert "locked" in data["detail"].lower()

    @pytest.mark.api
    async def test_lockout_prevents_valid_login(self, async_client: AsyncClient, test_user: User):
        """Test that lockout prevents even valid login."""
        # Lock the account
        for i in range(5):
            await async_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": f"WrongPass{i}!"}
            )

        # Try with correct password - should still be locked
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        assert response.status_code == 403

    @pytest.mark.api
    async def test_admin_unlock_account(self, async_client: AsyncClient, test_user: User, admin_user: User):
        """Test admin can unlock account."""
        # First lock the account
        for i in range(5):
            await async_client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": f"WrongPass{i}!"}
            )

        # Login as admin
        admin_login = await async_client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"}
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Unlock the account
        response = await async_client.post(
            "/api/auth/unlock-account",
            json={"email": "test@example.com"},
            headers=admin_headers
        )
        assert response.status_code == 200

        # Now user should be able to login
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        assert response.status_code == 200

    @pytest.mark.api
    async def test_admin_cannot_unlock_without_permission(self, async_client: AsyncClient, test_user: User):
        """Test that non-admin cannot unlock account."""
        # Login as regular user
        user_login = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "TestPass123!"}
        )
        user_token = user_login.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # Try to unlock - should fail
        response = await async_client.post(
            "/api/auth/unlock-account",
            json={"email": "test@example.com"},
            headers=user_headers
        )
        assert response.status_code == 403

    @pytest.mark.api
    async def test_admin_lock_status(self, async_client: AsyncClient, test_user: User, admin_user: User):
        """Test admin can check lock status."""
        # Login as admin
        admin_login = await async_client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "AdminPass123!"}
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Check lock status
        response = await async_client.get(
            "/api/auth/lock-status/test@example.com",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "is_locked" in data
        assert "failed_attempts" in data