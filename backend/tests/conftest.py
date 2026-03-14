import os


os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-12345678901234567890")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://qshield:test123@localhost:5432/qshield_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")