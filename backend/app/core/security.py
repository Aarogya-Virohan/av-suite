"""
Module: security.py
Purpose: Authentication aur password security operations ko handle karna
Yeh module password hashing, verification, aur JWT token generation handle karta hai.
Yeh module crucial hai application security ke liye kyu ki sensitive operations
jaise password handling aur token creation yahan centralized hain.

Key Components:
- verify_password: Plain password ko hashed password se match karna
- get_password_hash: Password ko bcrypt se hash karna
- create_access_token: JWT token generate karna authentication ke liye

Security Considerations:
- bcrypt library use hota hai secure password hashing ke liye (rainbow table attack se protection)
- JWT tokens time-limited hote hain (expiration handling)
- Timezone-aware datetime use karte hain (UTC) taaki daylight saving na affect kare
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from typing import Any, Union
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Function ka purpose: User ka plain password hash se match karna
    Yeh function login time par use hota hai jab user apna password enter karta hai.
    bcrypt library use karte hain secure comparison ke liye (timing attack resistant).
    
    Input:
    - plain_password (str): User ne jo password enter kiya (plain text)
    - hashed_password (str): Database mein stored hashed password
    
    Output: bool
    - True: Password match ho gaya, user authentication successful
    - False: Password match nahi hua, authentication failed
    
    Error: 
    - Invalid hashed password format to exception raise hoga
    - Handle karna padding-related errors
    
    Security Notes:
    - bcrypt automatically handles salt verification
    - Timing attack resistant hai (constant time comparison)
    - Never plain passwords ko log karo
    
    Usage:
    if verify_password(user_input_password, user.password_hash):
        # Generate JWT token
    else:
        # Return authentication failed error
    """
    
    try:
        # Encode passwords ko bytes format mein convert karte hain
        # bcrypt library bytes expect karta hai not strings
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # bcrypt.checkpw constant-time comparison use karta hai
        # Yeh timing attacks se protection provide karta hai
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        # Log karte hain error ko debugging ke liye
        # Lekin exception ko swallow karte hain security ke liye (no info leak)
        logger.error(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Function ka purpose: Plain password ko bcrypt hash mein convert karna
    Yeh function signup/password reset time par use hota hai.
    Database mein plain password kabhi store nahi karte, hamesha hash store karte hain.
    
    Input: password (str) - User ka plain password (unhashed)
    
    Output: str - Hashed password jo database mein store hoga
    
    Error: 
    - Invalid password encoding to exception raise hoga
    
    Security Notes:
    - bcrypt automatically random salt generate karta hai har call mein
    - Same password alag hash banta hai (salt due to)
    - Bcrypt rounds count: 12 (default, secure but kuch slow)
    - NEVER plain passwords ko log karo, hamesha hash karo
    
    Usage:
    hashed = get_password_hash(user_input_password)
    user.password_hash = hashed
    db.add(user)
    await db.commit()
    """
    
    try:
        # gensalt(): Random salt generate karta hai
        # Rounds=12 is default bcrypt security level
        # Higher rounds = more secure but slower (12 is good balance)
        salt = bcrypt.gensalt(rounds=12)
        
        # hashpw: Password ko salt se hash karta hai
        # Plain text se bytes, hash se bytes, then decode to string
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Database mein store karne ke liye string convert karte hain
        hashed_string = hashed.decode('utf-8')
        
        logger.debug("Password hashed successfully")
        return hashed_string
        
    except Exception as e:
        # Log error but don't expose details to user
        # Sensitive operation hai to security important
        logger.error(f"Password hashing error: {str(e)}")
        raise


def create_access_token(
    subject: Union[str, Any],
    clinic_id: str,
    role: str,
    expires_delta: timedelta = None
) -> str:
    """
    Function ka purpose: JWT access token generate karna
    Yeh function user login ke baad JWT token create karta hai.
    Token bearer token ke taur pe use hota hai authenticated requests mein.
    
    Input:
    - subject (Union[str, Any]): User ID ya unique identifier
    - clinic_id (str): Clinic ID (multi-tenant support ke liye)
    - role (str): User role (admin, doctor, patient, etc.)
    - expires_delta (timedelta, optional): Custom expiration time. Default: settings.JWT_EXPIRE_MINUTES
    
    Output: str - Encoded JWT token jo client ko send karte hain
    
    Error:
    - Invalid parameters to exception raise hoga
    - JWT encoding error (rare, agar invalid settings)
    
    Security Notes:
    - Token mein patient data nahi hota (sensitive data hota hai database mein)
    - Expiration time set hota hai to prevent long-term token abuse
    - Clinic_id include karte hain isolation ensure karne ke liye (multi-tenant)
    - Role based authorization ke liye token mein role include karte hain
    - iat (issued at) claim taaki freshness verify kar sakein
    
    Token Payload Example:
    {
        "sub": "user_id_123",           # Subject (user identifier)
        "clinic_id": "clinic_456",      # Clinic isolation
        "role": "doctor",               # Authorization
        "exp": 1234567890,              # Expiration timestamp
        "iat": 1234567000               # Issued at timestamp
    }
    
    Usage:
    token = create_access_token(
        subject=user.id,
        clinic_id=user.clinic_id,
        role=user.role
    )
    return {"access_token": token, "token_type": "bearer"}
    """
    
    try:
        # Expiration time calculate karte hain
        # Custom expires_delta ho to use karte hain, otherwise default
        if expires_delta:
            # Custom expiration time specified hai
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # Default expiration from settings (usually 24 hours)
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        
        # Token payload prepare karte hain
        # Yeh claims JWT token mein encode hote hain
        to_encode = {
            "sub": str(subject),                    # User ID
            "clinic_id": str(clinic_id),            # Clinic isolation
            "role": role,                           # Authorization role
            "exp": expire,                          # Expiration time
            "iat": datetime.now(timezone.utc),      # Issued at (freshness)
        }
        
        # JWT token encode karte hain SECRET_KEY aur algorithm se
        # Result: signed aur base64 encoded string
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info(f"Access token created for user: {subject}, clinic: {clinic_id}")
        return encoded_jwt
        
    except Exception as e:
        # Error log karte hain security issues detect karne ke liye
        logger.error(f"Token creation error: {str(e)}")
        raise


def decode_token(token: str) -> dict:
    """
    Function ka purpose: JWT token ko decode aur verify karna
    Yeh function request headers se token validate karta hai.
    Token valid na ho to exception raise hota hai.
    
    Input: token (str) - JWT bearer token
    
    Output: dict - Decoded token claims (subject, clinic_id, role, etc.)
    
    Error:
    - ExpiredSignatureError: Token expired ho gaya
    - JWTError: Token invalid ya tampered hai
    - Invalid SECRET_KEY ya algorithm mismatch
    
    Usage:
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        clinic_id = payload.get("clinic_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    """
    
    try:
        # JWT token ko decode aur verify karte hain
        # SECRET_KEY se signature verify hota hai (tampering detect karta hai)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        # Token expiration time exceed ho gaya
        logger.warning(f"Token expired")
        raise
        
    except JWTError as e:
        # Token invalid, tampered, ya corrupted hai
        logger.warning(f"Token validation failed: {str(e)}")
        raise
