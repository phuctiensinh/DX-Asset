import asyncio
import pytest
import httpx
from app.services.storage_service import StorageService
from app.utils.file_validation import validate_file_security

def test_real_seaweedfs_filer_ping():
    async def _run():
        filer_url = StorageService._get_filer_url()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{filer_url}/")
                assert res.status_code in (200, 404, 405)
        except Exception as e:
            pytest.skip(f"SeaweedFS container not reachable at {filer_url}: {e}")
    asyncio.run(_run())

def test_real_seaweedfs_upload_download_delete_cycle():
    async def _run():
        filer_url = StorageService._get_filer_url()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{filer_url}/")
        except Exception:
            pytest.skip("SeaweedFS container is offline, skipping real E2E test.")

        test_ticket = "INC-TEST-E2E-001"
        filename = "real_test_image.jpg"
        valid_jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00" + b"REAL_SEAWEEDFS_TEST_PAYLOAD"
        mime = "image/jpeg"

        ext, validated_mime = validate_file_security(valid_jpg_content, filename, mime, max_size_mb=10)
        assert ext == ".jpg"
        assert validated_mime == "image/jpeg"

        rel_path = await StorageService.upload_file(test_ticket, filename, valid_jpg_content, mime)
        assert rel_path.startswith(f"incidents/{test_ticket}/")

        downloaded_bytes, downloaded_mime = await StorageService.download_file(rel_path)
        assert downloaded_bytes == valid_jpg_content

        deleted = await StorageService.delete_file(rel_path)
        assert deleted is True

        with pytest.raises(Exception):
            await StorageService.download_file(rel_path)

    asyncio.run(_run())
