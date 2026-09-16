# Auth Service Unit Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.auth.service import AuthService
from app.modules.users.models import User
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationException


class TestAuthService:
    """Tests for AuthService."""

    @pytest_asyncio.fixture
    async def auth_service(self, db_session):
        return AuthService(db_session)

    @pytest_asyncio.fixture
    async def test_user(self, db_session, test_firm):
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

    @pytest.mark.unit
    async def test_validate_password_policy_valid(self, auth_service):
        """Test password policy validation with valid password."""
        is_valid, errors = auth_service.validate_password_policy("ValidPass123!")
        assert is_valid is True
        assert errors == []

    @pytest.mark.unit
    async def test_validate_password_policy_too_short(self, auth_service):
        """Test password policy validation with too short password."""
        is_valid, errors = auth_service.validate_password_policy("Short1!")
        assert is_valid is False
        assert "at least 12 characters" in errors[0]

    @pytest.mark.unit
    async def test_validate_password_policy_no_uppercase(self, auth_service):
        """Test password policy validation with no uppercase."""
        is_valid, errors = auth_service.validate_password_policy("validpass123!")
        assert is_valid is False
        assert "uppercase" in errors[0]

    @pytest.mark.unit
    async def test_validate_password_policy_no_lowercase(self, auth_service):
        """Test password policy validation with no lowercase."""
        is_valid, errors = auth_service.validate_password_policy("VALIDPASS123!")
        assert is_valid is False
        assert "lowercase" in errors[0]

    @pytest.mark.unit
    async def test_validate_password_policy_no_digit(self, auth_service):
        """Test password policy validation with no digit."""
        is_valid, errors = auth_service.validate_password_policy("ValidPassword!")
        assert is_valid is False
        assert "digit" in errors[0]

    @pytest.mark.unit
    async def test_validate_password_policy_no_special(self, auth_service):
        """Test password policy validation with no special character."""
        is_valid, errors = auth_service.validate_password_policy("ValidPass123")
        assert is_valid is False
        assert "special character" in errors[0]

    @pytest.mark.unit
    async def test_authenticate_valid_credentials(self, auth_service, test_user):
        """Test authentication with valid credentials."""
        user = await auth_service.authenticate("test@example.com", "TestPass123!")
        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.unit
    async def test_authenticate_invalid_email(self, auth_service, test_user):
        """Test authentication with non-existent email."""
        user = await auth_service.authenticate("nonexistent@example.com", "TestPass123!")
        assert user is None

    @pytest.mark.unit
    async def test_authenticate_invalid_password(self, auth_service, test_user):
        """Test authentication with wrong password."""
        user = await auth_service.authenticate("test@example.com", "WrongPass123!")
        assert user is None

    @pytest.mark.unit
    async def test_authenticate_inactive_user(self, auth_service, test_firm, db_session):
        """Test authentication with inactive user."""
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Inactive User",
            tenant_id=test_firm.id,
            roles=["associate"],
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()
        
        user = await auth_service.authenticate("inactive@example.com", "TestPass123!")
        assert user is None

    @pytest.mark.unit
    async def test_create_user_valid(self, auth_service, test_firm):
        """Test creating a user with valid password."""
        user = await auth_service.create_user(
            email="newuser@example.com",
            password="ValidPass123!",
            full_name="New User",
            tenant_id=test_firm.id,
        )
        assert user is not None
        assert user.email == "newuser@example.com"
        assert verify_password("ValidPass123!", user.hashed_password)

    @pytest.mark.unit
    async def test_create_user_invalid_password(self, auth_service, test_firm):
        """Test creating a user with invalid password."""
        with pytest.raises(ValueError) as exc_info:
            await auth_service.create_user(
                email="newuser@example.com",
                password="weak",
                full_name="New User",
                tenant_id=test_firm.id,
            )
        assert "Password does not meet policy" in str(exc_info.value)

    @pytest.mark.unit
    async def test_change_password_success(self, auth_service, test_user):
        """Test successful password change."""
        success, errors = await auth_service.change_password(
            test_user, "TestPass123!", "NewValidPass123!"
        )
        assert success is True
        assert errors == []
        # Verify new password works
        assert verify_password("NewValidPass123!", test_user.hashed_password)

    @pytest.mark.unit
    async def test_change_password_wrong_current(self, auth_service, test_user):
        """Test password change with wrong current password."""
        success, errors = await auth_service.change_password(
            test_user, "WrongPass123!", "NewValidPass123!"
        )
        assert success is False
        assert "Current password is incorrect" in errors

    @pytest.mark.unit
    async def test_change_password_same_as_current(self, auth_service, test_user):
        """Test password change with same password."""
        success, errors = await auth_service.change_password(
            test_user, "TestPass123!", "TestPass123!"
        )
        assert success is False
        assert "different from current password" in errors[0]

    @pytest.mark.unit
    async def test_change_password_invalid_new(self, auth_service, test_user):
        """Test password change with invalid new password."""
        success, errors = await auth_service.change_password(
            test_user, "TestPass123!", "weak"
        )
        assert success is False
        assert len(errors) > 0

    @pytest.mark.unit
    async def test_reset_password_success(self, auth_service, test_user):
        """Test successful password reset."""
        success, errors = await auth_service.reset_password(
            "test@example.com", "NewValidPass123!"
        )
        assert success is True
        assert errors == []
        assert verify_password("NewValidPass123!", test_user.hashed_password)

    @pytest.mark.unit
    async def test_reset_password_user_not_found(self, auth_service):
        """Test password reset for non-existent user."""
        success, errors = await auth_service.reset_password(
            "nonexistent@example.com", "NewValidPass123!"
        )
        assert success is False
        assert "User not found" in errors

    @pytest.mark.unit
    async def test_reset_password_invalid_new(self, auth_service, test_user):
        """Test password reset with invalid new password."""
        success, errors = await auth_service.reset_password(
            "test@example.com", "weak"
        )
        assert success is False
        assert len(errors) > 0


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    @pytest.mark.unit
    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        hashed = hash_password("TestPass123!")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    @pytest.mark.unit
    def test_hash_password_deterministic_different(self):
        """Test that same password produces different hashes."""
        hashed1 = hash_password("TestPass123!")
        hashed2 = hash_password("TestPass123!")
        assert hashed1 != hashed2  # Argon2 uses random salt

    @pytest.mark.unit
    def test_verify_password_correct(self):
        """Test verifying correct password."""
        hashed = hash_password("TestPass123!")
        assert verify_password("TestPass123!", hashed) is True

    @pytest.mark.unit
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        hashed = hash_password("TestPass123!")
        assert verify_password("WrongPass123!", hashed) is False

    @pytest.mark.unit
    def test_verify_password_empty_hash(self):
        """Test verifying against empty hash."""
        assert verify_password("TestPass123!", "") is False

    @pytest.mark.unit
    def test_verify_password_invalid_hash(self):
        """Test verifying against invalid hash format."""
        assert verify_password("TestPass123!", "invalid-hash") is False