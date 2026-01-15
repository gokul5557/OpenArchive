import os
from typing import List

class Settings:
    # Core
    CORE_API_KEY: str = os.getenv("CORE_API_KEY", "secret")
    OPENARCHIVE_MASTER_KEY: str = os.getenv("OPENARCHIVE_MASTER_KEY", "change-this-to-a-very-long-random-string-in-production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ALLOWED_SMTP_IPS: str = os.getenv("ALLOWED_SMTP_IPS", "127.0.0.1,172.16.0.0/12,192.168.0.0/16")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/archive")

    # Storage (MinIO)
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "admin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "password")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "archive-blobs")

    # Search (MeiliSearch)
    MEILI_HTTP_ADDR: str = os.getenv("MEILI_HTTP_ADDR", "http://meilisearch:7700")
    MEILI_MASTER_KEY: str = os.getenv("MEILI_MASTER_KEY", "masterKey")

    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "supersecretkeywhichshouldbechangedinprod")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 Hours

    # Integrity
    SYSTEM_SECRET: str = os.getenv("OPENARCHIVE_INTEGRITY_KEY", "super-secret-integrity-key-123456")

settings = Settings()
