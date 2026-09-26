import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from app.utils.file_validation import validate_file_security

def test_file_validation_valid_jpg():
    # Valid JPEG starts with \xFF\xD8\xFF
    fake_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"A" * 100
    ext, mime = validate_file_security(fake_jpg, "test.jpg", "image/jpeg", max_size_mb=10)
    assert ext == ".jpg"
    assert mime == "image/jpeg"

def test_file_validation_valid_png():
    # Valid PNG starts with \x89PNG\r\n\x1a\n
    fake_png = b"\x89PNG\r\n\x1a\n" + b"B" * 100
    ext, mime = validate_file_security(fake_png, "screenshot.png", "image/png", max_size_mb=10)
    assert ext == ".png"
    assert mime == "image/png"

def test_file_validation_valid_pdf():
    # Valid PDF starts with %PDF-
    fake_pdf = b"%PDF-1.7\n%abc" + b"C" * 100
    ext, mime = validate_file_security(fake_pdf, "document.pdf", "application/pdf", max_size_mb=10)
    assert ext == ".pdf"
    assert mime == "application/pdf"

def test_file_validation_invalid_magic_bytes():
    # Fake JPG (extension .jpg but content is plain text)
    fake_text_as_jpg = b"This is plain text pretending to be a JPG image."
    with pytest.raises(HTTPException) as exc_info:
        validate_file_security(fake_text_as_jpg, "malicious.jpg", "image/jpeg", max_size_mb=10)
    assert exc_info.value.status_code == 400
    assert "Magic Bytes Validation Failed" in exc_info.value.detail

def test_file_validation_invalid_extension():
    fake_exe = b"\x4d\x5a" # MZ executable
    with pytest.raises(HTTPException) as exc_info:
        validate_file_security(fake_exe, "virus.exe", "application/x-msdownload", max_size_mb=10)
    assert exc_info.value.status_code == 400
    assert "không được hỗ trợ" in exc_info.value.detail

def test_file_validation_oversized_file():
    huge_data = b"\xff\xd8\xff" + b"0" * (11 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc_info:
        validate_file_security(huge_data, "large.jpg", "image/jpeg", max_size_mb=10)
    assert exc_info.value.status_code == 413
    assert "vượt quá giới hạn" in exc_info.value.detail
