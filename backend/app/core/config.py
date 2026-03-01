"""
Q-Shield Configuration Module
Enterprise-grade configuration management with environment variable support.
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # Application
    APP_NAME: str = "Q-Shield"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Cryptographic Intelligence Platform for Post-Quantum Readiness"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = Field(default="/app/keys/jwt_private.pem")
    JWT_PUBLIC_KEY_PATH: str = Field(default="/app/keys/jwt_public.pem")
    
    # Platform Signing Keys (for Quantum-Safe Certificates)
    PLATFORM_SIGNING_KEY_PATH: str = Field(default="/app/keys/platform_signing.pem")
    PLATFORM_PUBLIC_KEY_PATH: str = Field(default="/app/keys/platform_public.pem")
    
    # Database
    DATABASE_URL: str = Field(...)
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)
    DATABASE_ECHO: bool = Field(default=False)
    
    # Redis (for caching and task queue)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = None
    
    # Scanning Configuration
    SCAN_TIMEOUT_SECONDS: int = Field(default=30)
    SCAN_MAX_CONCURRENT: int = Field(default=100)
    SCAN_RETRY_ATTEMPTS: int = Field(default=3)
    SCAN_BATCH_SIZE: int = Field(default=50)
    
    # Nmap Configuration
    NMAP_PATH: str = Field(default="/usr/bin/nmap")
    NMAP_ARGUMENTS: str = Field(default="-sV --script ssl-enum-ciphers,ssl-cert")
    
    # ZGrab2 Configuration
    ZGRAB2_PATH: str = Field(default="/usr/bin/zgrab2")
    ZGRAB2_TIMEOUT: int = Field(default=10)
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE_PATH: Optional[str] = Field(default="/var/log/qshield/app.log")
    AUDIT_LOG_PATH: Optional[str] = Field(default="/var/log/qshield/audit.log")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["https://dashboard.qshield.io"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])
    
    # OAuth Configuration
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    GOOGLE_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/google/callback")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    GITHUB_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/github/callback")
    
    # Microsoft OAuth
    MICROSOFT_CLIENT_ID: Optional[str] = Field(default=None)
    MICROSOFT_CLIENT_SECRET: Optional[str] = Field(default=None)
    MICROSOFT_TENANT_ID: str = Field(default="common")
    MICROSOFT_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/auth/microsoft/callback")
    
    # OAuth General Settings
    OAUTH_STATE_EXPIRY_MINUTES: int = Field(default=10)
    OAUTH_ALLOW_REGISTRATION: bool = Field(default=True)
    
    # Certificate Settings
    CERTIFICATE_VALIDITY_DAYS: int = Field(default=365)
    CERTIFICATE_VERIFICATION_URL: str = Field(default="https://verify.qshield.io/cert")
    
    # External Services
    WHOIS_API_KEY: Optional[str] = None
    SHODAN_API_KEY: Optional[str] = None
    CENSYS_API_ID: Optional[str] = None
    CENSYS_API_SECRET: Optional[str] = None
    
    # Compliance Standards
    NIST_SP_800_208_ENABLED: bool = True
    ISO_27001_ENABLED: bool = True
    RBI_CSF_ENABLED: bool = True
    
    # Feature Flags
    PQC_DETECTION_ENABLED: bool = True
    HYBRID_TLS_DETECTION_ENABLED: bool = True
    DOWNGRADE_ATTACK_DETECTION_ENABLED: bool = True
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


class DevelopmentSettings(Settings):
    """Development-specific settings."""
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    DATABASE_ECHO: bool = True
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


class StagingSettings(Settings):
    """Staging-specific settings."""
    ENVIRONMENT: str = "staging"
    LOG_LEVEL: str = "INFO"


class ProductionSettings(Settings):
    """Production-specific settings with stricter defaults."""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    DATABASE_ECHO: bool = False
    LOG_LEVEL: str = "WARNING"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance based on environment.
    Uses lru_cache for performance optimization.
    """
    env = os.getenv("ENVIRONMENT", "production")
    settings_map = {
        "development": DevelopmentSettings,
        "staging": StagingSettings,
        "production": ProductionSettings,
    }
    settings_class = settings_map.get(env, ProductionSettings)
    return settings_class()


# Export settings instance
settings = get_settings()
