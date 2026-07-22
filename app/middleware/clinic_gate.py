from __future__ import annotations

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.database import AsyncSessionLocal
from app.core.dependencies import get_authenticated_context


class ClinicGateMiddleware:
    """Attach authenticated clinic context to each tenant-scoped request."""

    _public_paths = (
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    )
    _public_path_prefixes = (
        "/api/v1/auth/",
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if self._is_public_request(request):
            await self.app(scope, receive, send)
            return

        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        token = self._extract_bearer_token(request.headers)
        if token is None:
            await JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Could not validate credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
            return

        try:
            async with AsyncSessionLocal() as session:
                auth_context = await self._resolve_context(token, session)
        except HTTPException as exc:
            await JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )(scope, receive, send)
            return

        request.state.authenticated_user = auth_context.user
        request.state.current_user = auth_context.user
        request.state.current_clinic = auth_context.clinic
        request.state.clinic_id = auth_context.clinic.id

        await self.app(scope, receive, send)

    async def _resolve_context(self, token: str, session: AsyncSession):
        return await get_authenticated_context(token, session)

    def _is_public_request(self, request: Request) -> bool:
        path = request.url.path
        if path in self._public_paths:
            return True
        return any(path.startswith(prefix) for prefix in self._public_path_prefixes)

    @staticmethod
    def _extract_bearer_token(headers: Headers) -> str | None:
        authorization = headers.get("authorization")
        if not authorization:
            return None

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None

        return token
