"""Size caps for uploads that are stored (pipeline report section E).

Without a cap a single 50 MB scan, read fully into memory, freezes one worker
and fills the bucket; a base64 logo was loaded on every authenticated request.
A request over a cap is answered with 413 and a plain message.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, UploadFile, status

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # patient documents: 10 MB
MAX_LOGO_BYTES = 256 * 1024  # clinic logo (decoded image): 256 KB
_MULTIPART_OVERHEAD = 64 * 1024  # form fields and boundaries around the file


def _mb(limit: int) -> str:
    return f"{limit / (1024 * 1024):g} MB" if limit >= 1024 * 1024 else f"{limit // 1024} KB"


def payload_too_large(what: str, limit: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        detail={
            "code": "FILE_TOO_LARGE",
            "message": f"{what} is too large. The limit is {_mb(limit)}. Please choose a smaller file.",
        },
    )


def reject_oversized_request(request: Request, limit: int, what: str) -> None:
    """Cheap early check on Content-Length, before the body is read."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + _MULTIPART_OVERHEAD:
        raise payload_too_large(what, limit)


async def read_capped(file: UploadFile, limit: int, what: str) -> bytes:
    """Read an upload, never holding more than limit + 1 bytes in memory."""
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise payload_too_large(what, limit)
    return data


def data_uri_decoded_size(value: str) -> int | None:
    """Decoded byte size of a base64 data URI, or None when it is not one."""
    if not value.startswith("data:") or "," not in value:
        return None
    payload = value.split(",", 1)[1]
    padding = payload.count("=", max(0, len(payload) - 2))
    return max(0, (len(payload) * 3) // 4 - padding)


def check_logo_size(value: str | None) -> None:
    """413 when a data-URI logo decodes to more than MAX_LOGO_BYTES."""
    if not value:
        return
    size = data_uri_decoded_size(value)
    # A plain URL is small by nature; anything else that is huge is refused too.
    if (size is not None and size > MAX_LOGO_BYTES) or (size is None and len(value) > 2048):
        raise payload_too_large("The logo", MAX_LOGO_BYTES)
