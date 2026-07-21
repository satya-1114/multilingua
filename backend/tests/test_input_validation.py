from __future__ import annotations

import pytest

from app.security.file_validation import (
    FileValidationError,
    validate_extension,
    validate_filename,
    validate_http_url,
    validate_mime,
    validate_size,
    validate_upload,
)


def test_filename_ok():
    assert validate_filename("report.pdf") == "report.pdf"


def test_filename_null_byte_rejected():
    with pytest.raises(FileValidationError):
        validate_filename("bad\x00.pdf")


def test_filename_path_traversal_rejected():
    with pytest.raises(FileValidationError):
        validate_filename("../etc/passwd")


def test_filename_strips_windows_path():
    assert validate_filename("C:\\Users\\x\\a.pdf") == "a.pdf"


def test_filename_double_dot_rejected():
    with pytest.raises(FileValidationError):
        validate_filename("..")


def test_filename_special_chars_rejected():
    with pytest.raises(FileValidationError):
        validate_filename("weird$name.pdf")


def test_extension_allowed():
    assert validate_extension("x.pdf") == ".pdf"


def test_extension_blocked():
    with pytest.raises(FileValidationError):
        validate_extension("x.exe")


def test_extension_unknown_rejected():
    with pytest.raises(FileValidationError):
        validate_extension("x.dat")


def test_extension_missing_rejected():
    with pytest.raises(FileValidationError):
        validate_extension("no_extension")


def test_mime_allowed():
    assert validate_mime("image/png") == "image/png"


def test_mime_rejected():
    with pytest.raises(FileValidationError):
        validate_mime("application/x-msdownload")


def test_mime_extension_mismatch_rejected():
    with pytest.raises(FileValidationError):
        validate_mime("image/png", name="x.jpg")


def test_mime_extension_consistent():
    assert validate_mime("image/png", name="x.png") == "image/png"


def test_size_ok():
    assert validate_size(1024) == 1024


def test_size_negative_rejected():
    with pytest.raises(FileValidationError):
        validate_size(-1)


def test_size_over_limit_rejected():
    with pytest.raises(FileValidationError):
        validate_size(10, limit=5)


def test_upload_all_at_once():
    r = validate_upload(name="x.pdf", mime="application/pdf", size=1000)
    assert r["name"] == "x.pdf"


def test_upload_rejects_dangerous_extension():
    with pytest.raises(FileValidationError):
        validate_upload(name="x.exe", mime="application/pdf", size=10)


def test_url_valid_http():
    assert validate_http_url("http://example.com/x").startswith("http://")


def test_url_valid_https():
    assert validate_http_url("https://a.b/c") == "https://a.b/c"


def test_url_javascript_scheme_rejected():
    with pytest.raises(FileValidationError):
        validate_http_url("javascript:alert(1)")


def test_url_require_https():
    with pytest.raises(FileValidationError):
        validate_http_url("http://a.b", require_https=True)


def test_url_empty_rejected():
    with pytest.raises(FileValidationError):
        validate_http_url("")
