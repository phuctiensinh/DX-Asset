import os
from typing import Tuple
from fastapi import HTTPException, status, UploadFile

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".pdf", ".docx", ".xlsx"
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

def validate_file_security(file_bytes: bytes, filename: str, content_type: str, max_size_mb: int = 10) -> Tuple[str, str]:
    """
    Validates file extension, reported MIME type, file size, and MAGIC BYTES (file signature).
    Raises HTTPException 400/413 if validation fails.
    Returns sanitized (extension, validated_mime_type).
    """
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tập tin đính kèm không có dữ liệu (0 bytes)."
        )

    # 1. Size Limit Check
    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dung lượng tập tin vượt quá giới hạn cho phép ({max_size_mb}MB)."
        )

    # 2. Extension Check
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng tập tin '{ext}' không được hỗ trợ. Chỉ chấp nhận: JPG, PNG, WEBP, PDF, DOCX, XLSX."
        )

    # 3. Reported MIME Type Check
    clean_mime = (content_type or "").lower().split(";")[0].strip()
    if clean_mime not in ALLOWED_MIME_TYPES:
        # Fallback MIME normalization based on extension
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        clean_mime = mime_map.get(ext, clean_mime)

    # 4. Magic Bytes Signature Check
    is_valid_signature = False

    if ext in (".jpg", ".jpeg"):
        # JPEG magic bytes: FF D8 FF
        is_valid_signature = file_bytes.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        is_valid_signature = file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == ".webp":
        # WEBP magic bytes: RIFF....WEBP
        is_valid_signature = file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[8:16]
    elif ext == ".pdf":
        # PDF magic bytes: %PDF-
        is_valid_signature = file_bytes.startswith(b"%PDF-")
    elif ext in (".docx", ".xlsx"):
        # OpenXML zip magic bytes: PK\x03\x04
        is_valid_signature = file_bytes.startswith(b"PK\x03\x04")

    if not is_valid_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nội dung dữ liệu của tập tin không khớp với định dạng '{ext}' (Magic Bytes Validation Failed)."
        )

    return ext, clean_mime
