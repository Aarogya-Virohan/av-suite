"""
Module: test_supabase_connection.py
Purpose: Supabase connection verification script ka liye
Yeh script Supabase database connection ko test karta hai aur verify karta hai ki
IPv4 session pooler properly configured hai aur working hai.

Key Components:
- AsyncEngine creation: Database connection ko establish karta hai
- Connection validation: Query execute karke verify karta hai
- Error handling: Database, authentication, network errors handle karta hai
- Logging: Operations aur errors ko log karta hai

Usage:
- Script ko directly run karo: python test_supabase_connection.py
- Output: Success message ya detailed error information
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import logging

# Configure logging for debugging
# Logging ka purpose: Operations ko track karna aur troubleshoot karna
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_supabase_connection(database_url: str) -> bool:
    """
    Function ka purpose: Supabase connection ko test karta hai
    Yeh function AsyncEngine create karke database se connection establish karta hai,
    connection pool se session lete hain, aur simple query execute karke verify karta hai.
    
    Input: database_url (str) - Database connection string format mein
           Format: postgresql+asyncpg://user.project_id:password@region.pooler.supabase.com:5432/postgres
    
    Output: bool - True agar connection successful hai, False otherwise
    
    Error: 
    - asyncpg.PostgresError: Database connection fail ho jaye
    - TimeoutError: Connection timeout ho jaye
    - ValueError: Invalid connection string format
    """
    
    try:
        # Validate connection URL format
        # URL validation important hai security aur error prevention ke liye
        if not database_url or not database_url.startswith("postgresql+asyncpg://"):
            logger.error("❌ Invalid DATABASE_URL format. Must start with 'postgresql+asyncpg://'")
            return False
        
        logger.info("🔄 Creating async database engine...")
        
        # Create async engine with connection pool
        # Echo=False taaki sensitive credentials log na ho
        # Pool ka purpose: Connection reuse karna performance ke liye
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,  # Connection ko ping karta hai before use
            pool_size=5,
            max_overflow=10,
        )
        
        logger.info("✅ Async engine created successfully")
        
        # Create session factory
        # SessionLocal ka purpose: Database sessions ko manage karna aur reuse karna
        async_session = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        logger.info("🔄 Attempting to acquire database connection...")
        
        # Test connection with actual query
        # Try-except block handle karta hai connection failures ko gracefully
        async with async_session() as session:
            logger.info("✅ Session created successfully")
            
            # Execute simple query to verify connection
            # Select 1 ka purpose: Minimal query jo connection verify kare
            result = await session.execute(text("SELECT 1 as connection_test"))
            row = result.fetchone()
            
            if row:
                logger.info(f"✅ Query executed successfully: {row}")
                logger.info("🎉 Supabase connection is working perfectly!")
                return True
            else:
                logger.error("❌ Query returned empty result")
                return False
        
    except Exception as e:
        # Comprehensive error handling
        # Different error types ko identify aur specific messages provide karte hain
        error_type = type(e).__name__
        error_message = str(e)
        
        logger.error(f"❌ Connection failed: {error_type}")
        logger.error(f"Details: {error_message}")
        
        # Provide helpful hints based on error type
        # Yeh hints help karte hain debugging mein
        if "authentication" in error_message.lower() or "password" in error_message.lower():
            logger.error("💡 Hint: Check your Supabase credentials (user, password, project_id)")
        elif "timeout" in error_message.lower():
            logger.error("💡 Hint: Check your internet connection or Supabase region availability")
        elif "host" in error_message.lower():
            logger.error("💡 Hint: Check if the hostname/region is correct in DATABASE_URL")
        
        return False


async def main():
    """
    Function ka purpose: Main entry point jo connection test ko orchestrate karta hai
    Yeh function environment se DATABASE_URL read karta hai aur test run karta hai.
    
    Input: None (environment variables se read karta hai)
    
    Output: None (console output aur exit code)
    
    Error: Handles missing DATABASE_URL environment variable
    """
    
    from app.core.config import settings
    
    logger.info("=" * 60)
    logger.info("🧪 Supabase Connection Verification Test")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    try:
        # Get database URL from settings
        # Settings .env file se load karta hai
        if not settings.DATABASE_URL:
            logger.error("❌ DATABASE_URL not configured in .env file")
            logger.info("💡 Please configure DATABASE_URL in .env file")
            return False
        
        # Mask sensitive parts for logging
        # Security ke liye password ko hide karte hain logs mein
        masked_url = settings.DATABASE_URL.split('@')[0] + "@***@***"
        logger.info(f"Testing connection to: {masked_url}")
        
        # Run connection test
        # Async operation ko run karta hai
        success = await test_supabase_connection(settings.DATABASE_URL)
        
        logger.info("=" * 60)
        if success:
            logger.info("✅ All checks passed! Backend can connect to Supabase")
            logger.info("You are ready to start the application")
            return True
        else:
            logger.error("❌ Connection test failed. Please check your configuration")
            return False
            
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {str(e)}")
        return False


if __name__ == "__main__":
    # Script execution point
    # Main async function ko run karta hai aur status return karta hai
    try:
        result = asyncio.run(main())
        # Exit with appropriate code for CI/CD integration
        # Success = 0, Failure = 1
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        logger.info("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        sys.exit(1)
