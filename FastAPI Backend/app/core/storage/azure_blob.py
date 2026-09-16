from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    ContainerClient,
    generate_blob_sas,
    BlobSasPermissions,
    ContentSettings,
)
from azure.identity import DefaultAzureCredential

from app.core.config import get_settings
from app.core.exceptions import StorageException

logger = logging.getLogger(__name__)

settings = get_settings()


class AzureBlobService:
    """Service for Azure Blob Storage operations with SAS URL generation."""

    def __init__(self, connection_string: str | None = None):
        self.connection_string = connection_string or settings.AZURE_BLOB_CONNECTION_STRING
        self.container_name = settings.AZURE_BLOB_CONTAINER
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None

    def _get_blob_service_client(self) -> BlobServiceClient:
        if self._blob_service_client is None:
            if self.connection_string:
                self._blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            else:
                credential = DefaultAzureCredential()
                account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"
                self._blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        return self._blob_service_client

    def _get_container_client(self) -> ContainerClient:
        if self._container_client is None:
            self._container_client = self._get_blob_service_client().get_container_client(self.container_name)
        return self._container_client

    async def ensure_container_exists(self) -> None:
        """Ensure the container exists, create if it doesn't."""
        try:
            container_client = self._get_container_client()
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except HttpResponseError as e:
            logger.error(f"Failed to create container: {e}")
            raise StorageException(f"Failed to create container: {e}")

    def get_blob_client(self, blob_name: str) -> BlobClient:
        """Get a blob client for the given blob name."""
        return self._get_container_client().get_blob_client(blob_name)

    def generate_upload_sas_url(
        self,
        blob_name: str,
        expiry_hours: int = 1,
        content_type: str | None = None,
    ) -> str:
        """Generate a SAS URL for uploading a blob."""
        sas_token = generate_blob_sas(
            account_name=self._get_blob_service_client().account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self._get_blob_service_client().credential.account_key
            if hasattr(self._get_blob_service_client().credential, "account_key")
            else None,
            permission=BlobSasPermissions(
                write=True,
                create=True,
                add=True,
            ),
            expiry=datetime.now(UTC) + timedelta(hours=expiry_hours),
            start=datetime.now(UTC) - timedelta(minutes=5),
        )
        blob_url = f"https://{self._get_blob_service_client().account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
        return blob_url

    def generate_download_sas_url(
        self,
        blob_name: str,
        expiry_hours: int = 1,
    ) -> str:
        """Generate a SAS URL for downloading a blob."""
        sas_token = generate_blob_sas(
            account_name=self._get_blob_service_client().account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self._get_blob_service_client().credential.account_key
            if hasattr(self._get_blob_service_client().credential, "account_key")
            else None,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(hours=expiry_hours),
            start=datetime.now(UTC) - timedelta(minutes=5),
        )
        blob_url = f"https://{self._get_blob_service_client().account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
        return blob_url

    async def upload_blob(
        self,
        blob_name: str,
        data: bytes,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        overwrite: bool = True,
    ) -> dict:
        """Upload a blob and return metadata."""
        blob_client = self.get_blob_client(blob_name)

        content_settings = ContentSettings(content_type=content_type) if content_type else None

        try:
            await blob_client.upload_blob(
                data,
                overwrite=overwrite,
                content_settings=content_settings,
                metadata=metadata or {},
            )

            properties = await blob_client.get_blob_properties()
            return {
                "blob_name": blob_name,
                "size": properties.size,
                "etag": properties.etag,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type,
            }
        except HttpResponseError as e:
            logger.error(f"Failed to upload blob {blob_name}: {e}")
            raise StorageException(f"Failed to upload blob: {e}")

    async def download_blob(self, blob_name: str) -> bytes:
        """Download a blob and return its content."""
        blob_client = self.get_blob_client(blob_name)
        try:
            stream = await blob_client.download_blob()
            return await stream.readall()
        except ResourceNotFoundError:
            raise StorageException(f"Blob not found: {blob_name}")
        except HttpResponseError as e:
            logger.error(f"Failed to download blob {blob_name}: {e}")
            raise StorageException(f"Failed to download blob: {e}")

    async def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob."""
        blob_client = self.get_blob_client(blob_name)
        try:
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
        except HttpResponseError as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            raise StorageException(f"Failed to delete blob: {e}")

    async def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists."""
        blob_client = self.get_blob_client(blob_name)
        try:
            await blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except HttpResponseError:
            return False

    async def get_blob_properties(self, blob_name: str) -> dict | None:
        """Get blob properties."""
        blob_client = self.get_blob_client(blob_name)
        try:
            properties = await blob_client.get_blob_properties()
            return {
                "blob_name": blob_name,
                "size": properties.size,
                "etag": properties.etag,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type,
                "metadata": properties.metadata,
            }
        except ResourceNotFoundError:
            return None

    async def verify_checksum(self, blob_name: str, expected_checksum: str, algorithm: str = "sha256") -> bool:
        """Verify blob checksum against expected value."""
        try:
            data = await self.download_blob(blob_name)
            if algorithm == "sha256":
                computed = hashlib.sha256(data).hexdigest()
            elif algorithm == "md5":
                computed = hashlib.md5(data).hexdigest()
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            return computed == expected_checksum
        except StorageException:
            return False

    async def copy_blob(
        self,
        source_blob_name: str,
        dest_blob_name: str,
        metadata: dict[str, str] | None = None,
    ) -> dict:
        """Copy a blob within the same container (for versioning)."""
        source_client = self.get_blob_client(source_blob_name)
        dest_client = self.get_blob_client(dest_blob_name)

        try:
            copy = await dest_client.start_copy_from_url(source_client.url, metadata=metadata)
            return {
                "copy_id": copy.get("copy_id"),
                "copy_status": copy.get("copy_status"),
            }
        except HttpResponseError as e:
            logger.error(f"Failed to copy blob {source_blob_name} to {dest_blob_name}: {e}")
            raise StorageException(f"Failed to copy blob: {e}")

    async def set_blob_metadata(self, blob_name: str, metadata: dict[str, str]) -> None:
        """Set blob metadata."""
        blob_client = self.get_blob_client(blob_name)
        try:
            await blob_client.set_blob_metadata(metadata)
        except HttpResponseError as e:
            logger.error(f"Failed to set metadata for blob {blob_name}: {e}")
            raise StorageException(f"Failed to set metadata: {e}")

    async def get_blob_metadata(self, blob_name: str) -> dict | None:
        """Get blob metadata."""
        blob_client = self.get_blob_client(blob_name)
        try:
            properties = await blob_client.get_blob_properties()
            return properties.metadata
        except ResourceNotFoundError:
            return None


# Singleton instance
_azure_blob_service: Optional[AzureBlobService] = None


def get_azure_blob_service() -> AzureBlobService:
    global _azure_blob_service
    if _azure_blob_service is None:
        _azure_blob_service = AzureBlobService()
    return _azure_blob_service