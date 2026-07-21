from __future__ import annotations


def test_csv_preview_reports_duplicates_and_invalid():
    from app.services.csv_import import audience_preview

    data = (
        "email,full_name,language\n"
        "alice@example.com,Alice,en\n"
        "alice@example.com,Alice Dup,en\n"
        "bad-email,No At,en\n"
    ).encode("utf-8")
    preview = audience_preview(data)
    report = preview["report"]
    assert report["total"] == 3
    assert report["invalid"] == 1
    assert report["duplicates"] == 1
    assert report["valid"] == 1


def test_export_renderers_produce_bytes():
    from app.services import export

    rows = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    csv_bytes, mime, name = export.render("csv", title="t", rows=rows)
    assert mime == "text/csv" and csv_bytes.startswith(b"a,b\n")
    json_bytes, mime, _ = export.render("json", title="t", rows=rows)
    assert mime == "application/json" and b'"a": 1' in json_bytes


def test_upload_signed_url_roundtrip():
    from app.services import upload

    url = upload.signed_url("/tmp/example.txt", expires_in=60)
    assert "sig=" in url and "exp=" in url
