"""File storage for the Student reports (Story 13.7, AD-14, AD-17, NFR-7).

One private bucket, `reports`. `put` stores bytes under a path, `signed_url` hands out a
short-lived download URL (`SIGNED_URL_TTL_SECONDS`, default 300), `delete` removes an object.
Callers ask for a signed URL only after `platform/authz` allowed the download (AD-12).

- With `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set: Supabase Storage over its REST api
  (`/storage/v1/object/...`), server side only.
- Without them, and only when `APP_ENV` is local, test or ci: the mock, files under
  `LOCAL_STORAGE_DIR` (default `.local-storage`, a volume shared by `backend` and
  `worker-batch` in compose). Its signed URL is `/api/storage/local/<bucket>/<path>?expires=…&
  signature=…`, an HMAC-SHA256 with the JWT secret, served by `router` (mounted only for the
  mock). Production refuses to start without the keys (Story 3.14), so it never falls back.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Protocol

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse

from app.platform import authz
from app.platform.config import get_settings
from app.platform.errors import error_response

__all__ = [
    "REPORTS",
    "LocalStorage",
    "Storage",
    "StorageError",
    "SupabaseStorage",
    "get_storage",
    "router",
    "uses_mock",
]

REPORTS = "reports"
"""The one private bucket (AD-14)."""

MEDIA_TYPES = {".pdf": "application/pdf", ".zip": "application/zip"}
"""What the mock serves its objects as: the Student report (Story 13.7) and the ZIP (13.13)."""

_SAFE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class StorageError(Exception):
    """A store, sign or delete that failed; the message never holds a key or a signature."""


class Storage(Protocol):
    async def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None: ...

    async def signed_url(self, bucket: str, path: str, *, download_name: str) -> str: ...

    async def delete(self, bucket: str, path: str) -> None: ...


def _checked(path: str) -> str:
    """An object path made of plain segments: no `..`, no leading slash, no backslash."""
    if not _SAFE_PATH.match(path) or ".." in path.split("/") or "//" in path:
        raise StorageError("invalid object path")
    return path


def _signature(bucket: str, path: str, expires: int, download_name: str) -> str:
    key = get_settings().jwt_secret.encode()
    message = f"storage\n{bucket}\n{path}\n{expires}\n{download_name}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


class LocalStorage:
    """The mock: files under `root` (AD-17)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def file(self, bucket: str, path: str) -> Path:
        return self.root / _checked(bucket) / _checked(path)

    async def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        target = self.file(bucket, path)

        def write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            # Written beside and renamed, so a download never reads half a file.
            partial = target.with_name(f"{target.name}.{secrets.token_hex(8)}.part")
            partial.write_bytes(data)
            partial.replace(target)

        await asyncio.to_thread(write)

    async def signed_url(self, bucket: str, path: str, *, download_name: str) -> str:
        _checked(path)
        expires = int(time.time()) + get_settings().signed_url_ttl_seconds
        query = urllib.parse.urlencode(
            {
                "expires": expires,
                "name": download_name,
                "signature": _signature(bucket, path, expires, download_name),
            }
        )
        return f"/api/storage/local/{bucket}/{path}?{query}"

    async def delete(self, bucket: str, path: str) -> None:
        target = self.file(bucket, path)
        await asyncio.to_thread(target.unlink, missing_ok=True)


class SupabaseStorage:
    """Supabase Storage over its REST api, with the service role key (server side only)."""

    def __init__(self, url: str, key: str, timeout: float = 20.0) -> None:
        self.url = url.rstrip("/")
        self.key = key
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, body: bytes | None, content_type: str) -> bytes:
        request = urllib.request.Request(
            f"{self.url}/storage/v1/{endpoint}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.key}",
                "apikey": self.key,
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as answer:  # noqa: S310
                return answer.read()
        except (urllib.error.URLError, TimeoutError) as failed:
            # The status only: the body could echo the request.
            status = getattr(failed, "code", None)
            raise StorageError(
                f"storage {method} failed ({status or type(failed).__name__})"
            ) from None

    async def put(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        endpoint = f"object/{_checked(bucket)}/{_checked(path)}"
        await asyncio.to_thread(self._request, "POST", endpoint, data, content_type)

    async def signed_url(self, bucket: str, path: str, *, download_name: str) -> str:
        endpoint = f"object/sign/{_checked(bucket)}/{_checked(path)}"
        body = json.dumps({"expiresIn": get_settings().signed_url_ttl_seconds}).encode()
        answer = await asyncio.to_thread(self._request, "POST", endpoint, body, "application/json")
        signed = json.loads(answer).get("signedURL")
        if not isinstance(signed, str) or not signed:
            raise StorageError("storage sign answered no URL")
        joiner = "&" if "?" in signed else "?"
        name = urllib.parse.quote(download_name)
        return f"{self.url}/storage/v1{signed}{joiner}download={name}"

    async def delete(self, bucket: str, path: str) -> None:
        body = json.dumps({"prefixes": [_checked(path)]}).encode()
        await asyncio.to_thread(
            self._request, "DELETE", f"object/{_checked(bucket)}", body, "application/json"
        )


def uses_mock() -> bool:
    """Whether the local mock serves storage: no keys, and not production (AD-17)."""
    settings = get_settings()
    keys = settings.supabase_url.strip() and settings.supabase_service_role_key.strip()
    return not keys and settings.app_env in ("local", "test", "ci")


def get_storage() -> Storage:
    settings = get_settings()
    if settings.supabase_url.strip() and settings.supabase_service_role_key.strip():
        return SupabaseStorage(settings.supabase_url, settings.supabase_service_role_key)
    if not uses_mock():
        raise StorageError("no storage keys")
    return LocalStorage(settings.local_storage_dir)


router = APIRouter(prefix="/api/storage/local", tags=["storage"], include_in_schema=False)


@router.get("/{bucket}/{path:path}", dependencies=[Depends(authz.public)])
async def local_download(
    bucket: str, path: str, expires: int = 0, name: str = "", signature: str = ""
):
    """The mock's signed download: the file while the signature holds and has not expired; 404
    `not_found` for anything else, one answer."""
    missing = error_response(404, "not_found", "No such file.")
    if not uses_mock() or expires < time.time():
        return missing
    try:
        wanted = _signature(bucket, path, expires, name)
        file = LocalStorage(get_settings().local_storage_dir).file(bucket, path)
    except StorageError:
        return missing
    if not signature.isascii() or not hmac.compare_digest(wanted, signature):
        return missing
    if not file.is_file():
        return missing
    response: FileResponse | JSONResponse = FileResponse(
        file,
        media_type=MEDIA_TYPES.get(file.suffix, "application/octet-stream"),
        filename=name or file.name,
        headers={"Cache-Control": "no-store"},
    )
    return response
