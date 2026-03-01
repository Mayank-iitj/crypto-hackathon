"""
Q-Shield Security Module
JWT authentication, password hashing, and security utilities.
"""

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes, PublicKeyTypes
from cryptography.hazmat.backends import default_backend
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str
    exp: datetime
    iat: datetime
    jti: str
    type: str  # "access" or "refresh"
    roles: list[str] = []
    permissions: list[str] = []


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def load_private_key(key_path: str) -> PrivateKeyTypes:
    """Load RSA private key from PEM file."""
    path = Path(key_path)
    if not path.exists():
        raise FileNotFoundError(f"Private key not found at {key_path}")
    
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key


def load_public_key(key_path: str) -> PublicKeyTypes:
    """Load RSA public key from PEM file."""
    path = Path(key_path)
    if not path.exists():
        raise FileNotFoundError(f"Public key not found at {key_path}")
    
    with open(path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )
    return public_key


def generate_key_pair(key_size: int = 4096) -> Tuple[bytes, bytes]:
    """
    Generate a new RSA key pair.
    Returns (private_key_pem, public_key_pem)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    roles: list[str] = None,
    permissions: list[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    now = datetime.now(timezone.utc)
    
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(32),
        "type": "access",
        "roles": roles or [],
        "permissions": permissions or [],
    }
    
    private_key = load_private_key(settings.JWT_PRIVATE_KEY_PATH)
    
    return jwt.encode(
        payload,
        private_key,
        algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    now = datetime.now(timezone.utc)
    
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": secrets.token_urlsafe(32),
        "type": "refresh",
    }
    
    private_key = load_private_key(settings.JWT_PRIVATE_KEY_PATH)
    
    return jwt.encode(
        payload,
        private_key,
        algorithm=settings.JWT_ALGORITHM
    )


def create_token_pair(
    subject: str,
    roles: list[str] = None,
    permissions: list[str] = None,
) -> TokenPair:
    """Create both access and refresh tokens."""
    access_token = create_access_token(subject, roles, permissions)
    refresh_token = create_refresh_token(subject)
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        public_key = load_public_key(settings.JWT_PUBLIC_KEY_PATH)
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return TokenPayload(**payload)
    except JWTError:
        return None


def validate_access_token(token: str) -> Optional[TokenPayload]:
    """Validate an access token and return payload."""
    payload = decode_token(token)
    if payload and payload.type == "access":
        return payload
    return None


def validate_refresh_token(token: str) -> Optional[TokenPayload]:
    """Validate a refresh token and return payload."""
    payload = decode_token(token)
    if payload and payload.type == "refresh":
        return payload
    return None


def sign_data(data: bytes, private_key_path: str = None) -> bytes:
    """Sign data using RSA-PSS with SHA-384."""
    key_path = private_key_path or settings.PLATFORM_SIGNING_KEY_PATH
    private_key = load_private_key(key_path)
    
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA384()),
            salt_length=padding.PSS.AUTO
        ),
        hashes.SHA384()
    )
    
    return signature


def verify_signature(
    data: bytes,
    signature: bytes,
    public_key_path: str = None
) -> bool:
    """Verify RSA-PSS signature."""
    key_path = public_key_path or settings.PLATFORM_PUBLIC_KEY_PATH
    public_key = load_public_key(key_path)
    
    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA384()),
                salt_length=padding.PSS.AUTO
            ),
            hashes.SHA384()
        )
        return True
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"qshield_{secrets.token_urlsafe(32)}"
