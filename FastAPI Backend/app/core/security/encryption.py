from __future__ import annotations

import base64
import logging

from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive PII fields.

    Uses Fernet (AES-128-GCM) for authenticated encryption.
    Supports key rotation via MultiFernet.
    """

    def __init__(self, key: str | None = None):
        """
        Initialize encryption service.

        Args:
            key: Base64-encoded 32-byte key. If None, loads from settings.
        """
        self._fernet: MultiFernet | None = None
        self._initialize(key)

    def _initialize(self, key: str | None) -> None:
        """Initialize Fernet/MultiFernet from key."""
        if key is None:
            settings = get_settings()
            key = settings.ENCRYPTION_KEY

        if not key:
            raise EncryptionError(
                "Encryption key not configured. Set ENCRYPTION_KEY environment variable."
            )

        try:
            # Support both single key and comma-separated multiple keys for rotation
            keys = [k.strip() for k in key.split(",") if k.strip()]
            if not keys:
                raise EncryptionError("No valid encryption keys provided")

            fernet_keys = []
            for k in keys:
                # Validate key format (base64, 32 bytes when decoded)
                try:
                    decoded = base64.urlsafe_b64decode(k)
                    if len(decoded) != 32:
                        raise ValueError(f"Key must be 32 bytes when decoded, got {len(decoded)}")
                    fernet_keys.append(Fernet(k))
                except Exception as e:
                    raise EncryptionError(f"Invalid encryption key format: {e}") from e

            self._fernet = MultiFernet(fernet_keys)
            logger.info("Encryption service initialized with %d key(s)", len(fernet_keys))

        except EncryptionError:
            raise
        except Exception as e:
            raise EncryptionError(f"Failed to initialize encryption: {e}") from e

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet-compatible encryption key."""
        return Fernet.generate_key().decode()

    @staticmethod
    def derive_key_from_password(password: str, salt: bytes | None = None) -> tuple[str, bytes]:
        """
        Derive a Fernet key from a password using PBKDF2.

        Args:
            password: Password to derive key from
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (base64-encoded key, salt)
        """
        if salt is None:
            import os
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt

    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted bytes (Fernet token)

        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            return b""

        if self._fernet is None:
            raise EncryptionError("Encryption service not initialized")

        try:
            return self._fernet.encrypt(plaintext.encode())
        except Exception as e:
            logger.exception("Encryption failed")
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: bytes) -> str:
        """
        Decrypt a ciphertext to plaintext string.

        Args:
            ciphertext: Encrypted bytes from encrypt()

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails (invalid token, wrong key, tampered data)
        """
        if not ciphertext:
            return ""

        if self._fernet is None:
            raise EncryptionError("Encryption service not initialized")

        try:
            return self._fernet.decrypt(ciphertext).decode()
        except Exception as e:
            logger.exception("Decryption failed")
            raise EncryptionError(f"Decryption failed: {e}") from e

    def encrypt_optional(self, plaintext: str | None) -> bytes | None:
        """Encrypt optional string, returning None if input is None/empty."""
        if plaintext is None or plaintext == "":
            return None
        return self.encrypt(plaintext)

    def decrypt_optional(self, ciphertext: bytes | None) -> str | None:
        """Decrypt optional bytes, returning None if input is None/empty."""
        if ciphertext is None or ciphertext == b"":
            return None
        return self.decrypt(ciphertext)


# Global singleton instance (initialized on first use)
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_field(plaintext: str | None) -> bytes | None:
    """Convenience function to encrypt a field value."""
    return get_encryption_service().encrypt_optional(plaintext)


def decrypt_field(ciphertext: bytes | None) -> str | None:
    """Convenience function to decrypt a field value."""
    return get_encryption_service().decrypt_optional(ciphertext)
