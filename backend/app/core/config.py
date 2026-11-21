"""
Module: config.py
Purpose: Application configuration settings ko centralize karna
Yeh module environment variables se application settings load karta hai
aur Pydantic validators ke through validation ensure karta hai.

Key Components:
- Settings class: Environment variables ko define aur validate karta hai
- cors_origins_list: CORS origins ko process karta hai comma-separated string se

Usage:
from app.core.config import settings
print(settings.ENVIRONMENT)
print(settings.JWT_EXPIRE_MINUTES)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationInfo, field_validator
import ipaddress
import re
from typing import List
import logging
import base64

logger = logging.getLogger(__name__)
_TEST_JWT_SECRET = "c1f230d789abcec1f230d789abcec1f230d789abcec1f230d789abcec1f230d7"
_TEST_PLATFORM_MFA_KEY = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
_JWT_PLACEHOLDERS = {"secret", "changeme", "change_me", "password", "your_secret_key", "test-secret-key"}


def _is_predictable_hex_secret(value: str) -> bool:
    lowered = value.lower()
    if len(set(lowered)) == 1 or lowered in _JWT_PLACEHOLDERS:
        return True
    if lowered == lowered[0] * len(lowered):
        return True
    if len(lowered) >= 8 and (lowered == (lowered[:8] * (len(lowered) // 8 + 1))[:len(lowered)]):
        return True
    ascending = "0123456789abcdef"
    descending = ascending[::-1]
    doubled = ascending * 2
    ascend_then_descend = ascending * 3 + descending
    if any(
        lowered in (sequence * 5)
        for sequence in (ascending, descending, doubled, ascend_then_descend)
    ):
        return True
    return False


def _has_patterned_bytes(value: bytes) -> bool:
    if len(set(value)) == 1:
        return True
    if value == bytes(range(32)) or value == bytes(range(32, 0, -1)):
        return True
    return any(value == value[:size] * (len(value) // size) + value[:len(value) % size] for size in range(1, 9))


class Settings(BaseSettings):
    """
    Class ka purpose: Application configuration ka central point
    Yeh class environment variables ko load karta hai .env file se
    aur type validation ensure karta hai Pydantic ke through.
    
    All settings yahan centralized hain taaki code mein hardcoding na ho
    aur environment-specific configuration easy ho sake.
    """
    
    # Application Environment Configuration
    # Environment type: development, staging, production
    # Development mein debug logs aur detailed error messages milte hain
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    # AUD-04: public self-signup (POST /auth/register) is off for launch.
    # Clinics are created only by scripts/clinic_setup (EN-4), which calls the
    # service directly. Re-opening needs captcha + review (launch-plan Later).
    SELF_SIGNUP_ENABLED: bool = False
    # BE-3 / M-1 / AUD-12: marketplace install/enable/disable are closed;
    # entitlements come from scripts/clinic_setup (and later the console).
    MARKETPLACE_WRITES_ENABLED: bool = False
    
    # API Configuration
    # API_V1_PREFIX: Versioning ke liye routes structure ko define karta hai
    # Version management important hai backward compatibility ke liye
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS Configuration
    # CORS (Cross-Origin Resource Sharing) frontend requests ko allow karta hai
    # Multiple origins comma-separated format mein define ho sakte hain (e.g. via .env)
    # Security important: only trusted origins ko allow karo
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Comma-separated trusted reverse-proxy IPs/CIDRs. Empty means no proxy
    # headers are trusted and request.client.host is always used.
    TRUSTED_PROXY_IPS: str = ""
    
    # Cloudflare Turnstile Configuration (Optional)
    TURNSTILE_SECRET_KEY: str | None = None

    # Database Configuration
    # DATABASE_URL: PostgreSQL async connection string
    # Format: postgresql+asyncpg://user.project:password@host:port/database
    # Supabase Session Pooler use karta hai IPv4 compatibility ke liye
    # Yeh required field hai - .env mein must set hona chahiye
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    
    # JWT (JSON Web Token) Configuration
    # JWT authentication stateless authentication provide karta hai
    # SECRET_KEY: Token signing/verification ke liye use hota hai
    # Must be strong aur random - generator: openssl rand -hex 32
    JWT_SECRET_KEY: str
    
    # JWT_ALGORITHM: Token signing algorithm
    # HS256 (HMAC with SHA-256) secure aur widely supported hai
    JWT_ALGORITHM: str = "HS256"
    
    # JWT_EXPIRE_MINUTES: Token validity period
    # 15 = 15 minutes (default for short-lived access tokens)
    # Shorter period = better security, longer period = better UX
    JWT_EXPIRE_MINUTES: int = 15

    PLATFORM_JWT_EXPIRE_MINUTES: int = Field(default=480, gt=0)
    PLATFORM_MFA_KEY: str
    
    # Redis Configuration (Optional)
    # Redis caching aur session management ke liye use hota hai
    # Default: localhost:6379 (local development ke liye)
    # Production mein proper Redis instance use karo
    REDIS_URL: str = "redis://localhost:6379"
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    SUPABASE_BUCKET_NAME: str = "documents"

    # Pydantic Model Configuration
    # Configuration dikhaata hai Pydantic ko kaise settings load karne hain
    model_config = SettingsConfigDict(
        env_file=".env",                # .env file se load karo
        env_file_encoding="utf-8",      # UTF-8 encoding taaki unicode handle ho
        extra="ignore",                 # Extra env vars ko ignore karo (strict mode)
        hide_input_in_errors=True,
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValueError("JWT_SECRET_KEY must be exactly 32 bytes encoded as hexadecimal")
        if _is_predictable_hex_secret(normalized):
            raise ValueError("JWT_SECRET_KEY must not be a placeholder or obvious pattern")
        if info.data.get("ENVIRONMENT", "development").lower() == "production" and normalized == _TEST_JWT_SECRET:
            raise ValueError("JWT_SECRET_KEY must be generated specifically for production")
        return value

    @field_validator("PLATFORM_MFA_KEY")
    @classmethod
    def validate_platform_mfa_key(cls, value: str, info: ValidationInfo) -> str:
        from cryptography.fernet import Fernet, InvalidToken

        try:
            Fernet(value.encode("ascii"))
            decoded_key = base64.urlsafe_b64decode(value.encode("ascii"))
            is_test_key = value == _TEST_PLATFORM_MFA_KEY
            if len(decoded_key) != 32 or (_has_patterned_bytes(decoded_key) and not is_test_key):
                raise ValueError("patterned Fernet key")
        except (ValueError, UnicodeEncodeError, InvalidToken) as exc:
            raise ValueError("PLATFORM_MFA_KEY must be a valid Fernet key from Fernet.generate_key()") from exc
        # The CI key is deliberately fixed for reproducible tests and must never be used in production.
        if info.data.get("ENVIRONMENT", "development").lower() == "production" and value == _TEST_PLATFORM_MFA_KEY:
            raise ValueError("PLATFORM_MFA_KEY must be generated specifically for production")
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins; wildcard origins are not allowed")
        return value

    @field_validator("TRUSTED_PROXY_IPS")
    @classmethod
    def validate_trusted_proxy_ips(cls, value: str) -> str:
        for proxy in (item.strip() for item in value.split(",")):
            if proxy:
                try:
                    ipaddress.ip_network(proxy, strict=False)
                except ValueError as exc:
                    raise ValueError(
                        "TRUSTED_PROXY_IPS must be comma-separated IP addresses or CIDR ranges"
                    ) from exc
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Property ka purpose: CORS origins string ko list mein convert karna
        CORS_ORIGINS comma-separated string format mein hai but
        FastAPI CORSMiddleware ko list of strings chahiye hota hai.
        
        Input: None (self.CORS_ORIGINS use karta hai)
        
        Output: List[str] - Individual origins ka list
        
        Example:
        Input string: "http://localhost:3000,http://localhost:3001"
        Output list: ["http://localhost:3000", "http://localhost:3001"]
        
        Edge case: Extra whitespace handling
        - "http://localhost:3000 , http://localhost:3001"
        - .strip() se spaces automatically remove ho jaate hain
        """
        
        # Split string by comma aur har origin se extra whitespace remove karo
        # strip() method leading/trailing spaces ko clean karta hai
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Singleton instance jo poore application mein use hota hai
# Settings ko ek baar load karte hain startup par
# Har request mein naya instance create nahi hota (performance benefit)
settings = Settings()
