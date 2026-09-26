import uuid
import logging
import httpx
from typing import Tuple, Optional
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    @staticmethod
    def _get_filer_url() -> str:
        url = settings.SEAWEEDFS_FILER_URL.rstrip("/")
        return url

    @classmethod
    async def upload_file(cls, ticket_code: str, file_name: str, file_bytes: bytes, mime_type: str) -> str:
        """
        Uploads file bytes to SeaweedFS Filer via HTTP PUT.
        Returns the relative path on SeaweedFS Filer (e.g. 'incidents/INC-001/uuid_name.png').
        """
        filer_url = cls._get_filer_url()
        ext_dot = file_name.rfind(".")
        clean_base = file_name[:ext_dot] if ext_dot != -1 else file_name
        clean_ext = file_name[ext_dot:] if ext_dot != -1 else ""

        # Sanitize name
        safe_base = "".join(c for c in clean_base if c.isalnum() or c in ("-", "_")).strip() or "file"
        unique_id = uuid.uuid4().hex[:8]
        unique_filename = f"{unique_id}_{safe_base}{clean_ext}"
        relative_path = f"incidents/{ticket_code}/{unique_filename}"

        full_url = f"{filer_url}/{relative_path}"

        headers = {
            "Content-Type": mime_type
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.put(full_url, content=file_bytes, headers=headers)
                if response.status_code not in (200, 201):
                    logger.error(f"SeaweedFS upload failed HTTP {response.status_code}: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Không thể lưu trữ tập tin trên hệ thống SeaweedFS (HTTP {response.status_code})."
                    )
            logger.info(f"Successfully uploaded file to SeaweedFS: {relative_path}")
            return relative_path
        except httpx.RequestError as exc:
            logger.error(f"SeaweedFS connection error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dịch vụ lưu trữ tập tin SeaweedFS không phản hồi."
            )

    @classmethod
    async def download_file(cls, relative_path: str) -> Tuple[bytes, str]:
        """
        Downloads file bytes from SeaweedFS Filer via HTTP GET.
        Returns (file_bytes, mime_type).
        """
        filer_url = cls._get_filer_url()
        full_url = f"{filer_url}/{relative_path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(full_url)
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Tập tin đính kèm không tồn tại trên hệ thống lưu trữ."
                    )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Lỗi đọc tập tin từ SeaweedFS (HTTP {response.status_code})."
                    )
                mime = response.headers.get("Content-Type", "application/octet-stream")
                return response.content, mime
        except httpx.RequestError as exc:
            logger.error(f"SeaweedFS download error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dịch vụ lưu trữ tập tin SeaweedFS không phản hồi."
            )

    @classmethod
    async def delete_file(cls, relative_path: str) -> bool:
        """
        Deletes file from SeaweedFS Filer via HTTP DELETE.
        Returns True if deleted or already gone.
        """
        filer_url = cls._get_filer_url()
        full_url = f"{filer_url}/{relative_path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(full_url)
                if response.status_code in (200, 202, 204, 404):
                    logger.info(f"Successfully deleted file from SeaweedFS: {relative_path}")
                    return True
                logger.warning(f"SeaweedFS delete returned HTTP {response.status_code}: {response.text}")
                return False
        except Exception as exc:
            logger.error(f"SeaweedFS delete exception: {exc}")
            return False
