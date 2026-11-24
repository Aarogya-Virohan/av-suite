"""Commit the request's database session before the response is sent.

Why: `get_db` used to commit after `yield`. Since FastAPI 0.118 the code after
a dependency's `yield` runs only after the response has gone to the client, so
a write could be answered with 200 and land in the database a moment later
(Control Center needed a 400 ms re-read to hide that). This ASGI middleware
sits directly above the router and commits the session stored by `get_db`
at the moment the response starts.

Rules:
- Only successful answers (status < 400) are committed here. An error answer is
  left to `get_db`, which rolls back when the route raised.
- If the commit itself fails, the original response is dropped and the client
  gets a 500 instead of a success for data that was not saved.
- Routes that already commit keep working: a second commit is a no-op.
"""

from __future__ import annotations

import json
import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

_FAILED_BODY = json.dumps(
    {"detail": {"code": "SAVE_FAILED", "message": "Your change could not be saved. Please try again."}}
).encode()


class CommitBeforeResponseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        replaced = False

        async def send_wrapper(message: Message) -> None:
            nonlocal replaced
            if replaced:
                return  # drop the rest of the original response
            if message["type"] == "http.response.start" and message["status"] < 400:
                session = scope.get("state", {}).get("db_session")
                if session is not None and session.in_transaction():
                    try:
                        await session.commit()
                    except Exception:
                        logger.exception("Commit before response failed")
                        try:
                            await session.rollback()
                        except Exception:
                            pass
                        replaced = True
                        await send(
                            {
                                "type": "http.response.start",
                                "status": 500,
                                "headers": [
                                    (b"content-type", b"application/json"),
                                    (b"content-length", str(len(_FAILED_BODY)).encode()),
                                ],
                            }
                        )
                        await send({"type": "http.response.body", "body": _FAILED_BODY})
                        return
            await send(message)

        await self.app(scope, receive, send_wrapper)
