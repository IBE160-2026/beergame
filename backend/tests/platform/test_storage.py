"""`platform/storage` (Story 13.7, AD-14, AD-17, NFR-7): the local mock and Supabase Storage over
its REST api. No network: the Supabase client's requests are caught before they leave."""

import io
import json
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

import pytest

from app.platform import storage
from app.platform.config import get_settings


@pytest.fixture
def settings(monkeypatch, tmp_path):
    current = get_settings()
    monkeypatch.setattr(current, "local_storage_dir", str(tmp_path))
    monkeypatch.setattr(current, "supabase_url", "")
    monkeypatch.setattr(current, "supabase_service_role_key", "")
    return current


async def test_the_mock_stores_signs_and_deletes_under_its_folder(settings, tmp_path):
    assert storage.uses_mock()
    store = storage.get_storage()
    assert isinstance(store, storage.LocalStorage)
    await store.put("reports", "class-sessions/a/b/student-report.pdf", b"%PDF-", "application/pdf")
    assert (tmp_path / "reports/class-sessions/a/b/student-report.pdf").read_bytes() == b"%PDF-"
    url = await store.signed_url(
        "reports", "class-sessions/a/b/student-report.pdf", download_name="r.pdf"
    )
    parts = urlsplit(url)
    assert parts.path == "/api/storage/local/reports/class-sessions/a/b/student-report.pdf"
    query = parse_qs(parts.query)
    assert int(query["expires"][0]) - time.time() == pytest.approx(
        settings.signed_url_ttl_seconds, abs=5
    )
    await store.delete("reports", "class-sessions/a/b/student-report.pdf")
    assert not (tmp_path / "reports/class-sessions/a/b/student-report.pdf").exists()


@pytest.mark.parametrize("path", ["../x.pdf", "/etc/x", "a/../../x", "a\\b", "", "a//b"])
async def test_a_path_outside_plain_segments_is_refused(settings, path):
    with pytest.raises(storage.StorageError):
        await storage.LocalStorage("x").put("reports", path, b"", "application/pdf")


def test_production_never_falls_back_to_the_mock(settings, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    assert not storage.uses_mock()
    with pytest.raises(storage.StorageError):
        storage.get_storage()
    monkeypatch.setattr(settings, "supabase_url", "https://p.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "service-key")
    assert isinstance(storage.get_storage(), storage.SupabaseStorage)


async def test_supabase_uploads_signs_and_deletes_over_rest(monkeypatch, settings):
    sent: list[urllib.request.Request] = []

    def urlopen(request, timeout):
        sent.append(request)
        body = b"{}"
        if "/object/sign/" in request.full_url:
            body = json.dumps({"signedURL": "/object/sign/reports/a/r.pdf?token=t"}).encode()
        return io.BytesIO(body)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    store = storage.SupabaseStorage("https://p.supabase.co/", "service-key")
    await store.put("reports", "a/r.pdf", b"%PDF-", "application/pdf")
    url = await store.signed_url("reports", "a/r.pdf", download_name="studentrapport.pdf")
    await store.delete("reports", "a/r.pdf")
    upload, sign, remove = sent
    assert (upload.get_method(), upload.full_url) == (
        "POST",
        "https://p.supabase.co/storage/v1/object/reports/a/r.pdf",
    )
    assert upload.get_header("Authorization") == "Bearer service-key"
    assert upload.get_header("X-upsert") == "true"
    assert sign.full_url == "https://p.supabase.co/storage/v1/object/sign/reports/a/r.pdf"
    assert json.loads(sign.data) == {"expiresIn": settings.signed_url_ttl_seconds}
    assert url == (
        "https://p.supabase.co/storage/v1/object/sign/reports/a/r.pdf?token=t"
        "&download=studentrapport.pdf"
    )
    assert (remove.get_method(), json.loads(remove.data)) == ("DELETE", {"prefixes": ["a/r.pdf"]})


async def test_a_failed_supabase_call_names_no_key(monkeypatch):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "no", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(storage.StorageError) as failed:
        await storage.SupabaseStorage("https://p.supabase.co", "service-key").put(
            "reports", "a/r.pdf", b"", "application/pdf"
        )
    assert "service-key" not in str(failed.value) and "403" in str(failed.value)
