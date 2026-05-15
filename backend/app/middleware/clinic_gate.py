from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
from app.core.config import settings

class ClinicGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Only intercept /api/v1/* except /api/v1/auth/*
        if not path.startswith(settings.API_V1_PREFIX) or path.startswith(f"{settings.API_V1_PREFIX}/auth"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "data": None,
                    "meta": {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Missing or invalid token"
                        }
                    }
                }
            )

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            clinic_id = payload.get("clinic_id")
            user_id = payload.get("sub")
            role = payload.get("role")
            
            if not clinic_id or not user_id or not role:
                raise JWTError("Invalid token payload")

            request.state.clinic_id = clinic_id
            request.state.user_id = user_id
            request.state.role = role

        except JWTError:
            return JSONResponse(
                status_code=401,
                content={
                    "data": None,
                    "meta": {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Invalid or expired token"
                        }
                    }
                }
            )

        response = await call_next(request)
        return response
