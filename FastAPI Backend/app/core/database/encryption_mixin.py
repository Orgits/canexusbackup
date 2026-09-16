from __future__ import annotations

from sqlalchemy import LargeBinary
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security.encryption import decrypt_field, encrypt_field


class EncryptedFieldMixin:
    """
    Mixin providing transparent encryption/decryption for model fields.

    Usage:
        class MyModel(Base, EncryptedFieldMixin):
            _pan_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

            @hybrid_property
            def pan(self) -> Optional[str]:
                return self._decrypt(self._pan_encrypted)

            @pan.setter
            def pan(self, value: Optional[str]) -> None:
                self._pan_encrypted = self._encrypt(value)

    The mixin provides _encrypt and _decrypt methods using the global EncryptionService.
    """

    def _encrypt(self, value: str | None) -> bytes | None:
        """Encrypt a plaintext value for storage."""
        return encrypt_field(value)

    def _decrypt(self, value: bytes | None) -> str | None:
        """Decrypt a ciphertext value for access."""
        return decrypt_field(value)


def encrypted_column(
    nullable: bool = True,
    comment: str | None = None,
) -> Mapped[bytes | None]:
    """
    Create a mapped column for encrypted data storage.

    Args:
        nullable: Whether the column can be NULL
        comment: Optional column comment

    Returns:
        Mapped column configured for LargeBinary encrypted storage
    """
    return mapped_column(
        LargeBinary,
        nullable=nullable,
        comment=comment or "Encrypted PII data (Fernet AES-128-GCM)",
    )


class PIIEncryptionMixin:
    """
    Mixin that provides encrypted property accessors for common PII fields.

    Include this mixin in models that need encrypted PII fields.
    Define the `_encrypted` columns in the model, then the properties
    will handle transparent encryption/decryption.
    """

    # These properties expect corresponding _encrypted columns to be defined
    # in the model class. Override as needed.

    @hybrid_property
    def pan(self) -> str | None:
        return self._decrypt(getattr(self, "_pan_encrypted", None))

    @pan.setter
    def pan(self, value: str | None) -> None:
        self._pan_encrypted = self._encrypt(value)

    @hybrid_property
    def gstin(self) -> str | None:
        return self._decrypt(getattr(self, "_gstin_encrypted", None))

    @gstin.setter
    def gstin(self, value: str | None) -> None:
        self._gstin_encrypted = self._encrypt(value)

    @hybrid_property
    def tan(self) -> str | None:
        return self._decrypt(getattr(self, "_tan_encrypted", None))

    @tan.setter
    def tan(self, value: str | None) -> None:
        self._tan_encrypted = self._encrypt(value)

    @hybrid_property
    def cin(self) -> str | None:
        return self._decrypt(getattr(self, "_cin_encrypted", None))

    @cin.setter
    def cin(self, value: str | None) -> None:
        self._cin_encrypted = self._encrypt(value)

    @hybrid_property
    def din(self) -> str | None:
        return self._decrypt(getattr(self, "_din_encrypted", None))

    @din.setter
    def din(self, value: str | None) -> None:
        self._din_encrypted = self._encrypt(value)

    @hybrid_property
    def aadhaar(self) -> str | None:
        return self._decrypt(getattr(self, "_aadhaar_encrypted", None))

    @aadhaar.setter
    def aadhaar(self, value: str | None) -> None:
        self._aadhaar_encrypted = self._encrypt(value)

    @hybrid_property
    def passport(self) -> str | None:
        return self._decrypt(getattr(self, "_passport_encrypted", None))

    @passport.setter
    def passport(self, value: str | None) -> None:
        self._passport_encrypted = self._encrypt(value)

    @hybrid_property
    def deductee_pan(self) -> str | None:
        return self._decrypt(getattr(self, "_deductee_pan_encrypted", None))

    @deductee_pan.setter
    def deductee_pan(self, value: str | None) -> None:
        self._deductee_pan_encrypted = self._encrypt(value)
