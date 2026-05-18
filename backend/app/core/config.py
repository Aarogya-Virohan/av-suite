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
from typing import List
import logging

logger = logging.getLogger(__name__)


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
    
    # API Configuration
    # API_V1_PREFIX: Versioning ke liye routes structure ko define karta hai
    # Version management important hai backward compatibility ke liye
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS Configuration
    # CORS (Cross-Origin Resource Sharing) frontend requests ko allow karta hai
    # Multiple origins comma-separated format mein define ho sakte hain
    # Security important: only trusted origins ko allow karo
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    
    # Database Configuration
    # DATABASE_URL: PostgreSQL async connection string
    # Format: postgresql+asyncpg://user.project:password@host:port/database
    # Supabase Session Pooler use karta hai IPv4 compatibility ke liye
    # Yeh required field hai - .env mein must set hona chahiye
    DATABASE_URL: str
    
    # JWT (JSON Web Token) Configuration
    # JWT authentication stateless authentication provide karta hai
    # SECRET_KEY: Token signing/verification ke liye use hota hai
    # Must be strong aur random - generator: openssl rand -hex 32
    JWT_SECRET_KEY: str
    
    # JWT_ALGORITHM: Token signing algorithm
    # HS256 (HMAC with SHA-256) secure aur widely supported hai
    JWT_ALGORITHM: str = "HS256"
    
    # JWT_EXPIRE_MINUTES: Token validity period
    # 1440 = 24 hours (default)
    # Shorter period = better security, longer period = better UX
    JWT_EXPIRE_MINUTES: int = 1440
    
    # Redis Configuration (Optional)
    # Redis caching aur session management ke liye use hota hai
    # Default: localhost:6379 (local development ke liye)
    # Production mein proper Redis instance use karo
    REDIS_URL: str = "redis://localhost:6379"

    # Pydantic Model Configuration
    # Configuration dikhaata hai Pydantic ko kaise settings load karne hain
    model_config = SettingsConfigDict(
        env_file=".env",                # .env file se load karo
        env_file_encoding="utf-8",      # UTF-8 encoding taaki unicode handle ho
        extra="ignore",                 # Extra env vars ko ignore karo (strict mode)
    )

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
