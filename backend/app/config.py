"""
Application configuration module.

PRIVACY & CONSENT NOTICE:
This application processes biometric data (facial images and embeddings).
Before deploying, ensure you have:
1. Obtained explicit consent from all users whose faces will be registered
2. Informed users about how their biometric data will be stored and used
3. Implemented appropriate data retention and deletion policies
4. Complied with local privacy laws (GDPR, CCPA, etc.)
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Face Attendance System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./data/db/attendance.db"

    SECRET_KEY: str = "change-this-in-production-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    FACE_MATCH_THRESHOLD: float = 0.6
    DUPLICATE_ATTENDANCE_TIMEOUT_MINUTES: int = 30

    CAMERA_INDEX: int = 0
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    FACE_DETECTION_MODEL: str = "hog"

    DATA_DIR: Path = Path("/app/data")
    FACES_DIR: Path = Path("/app/data/faces")
    EXPORTS_DIR: Path = Path("/app/data/exports")
    LOGS_DIR: Path = Path("/app/data/logs")

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def ensure_directories():
    settings = get_settings()
    for dir_path in [settings.DATA_DIR, settings.FACES_DIR, settings.EXPORTS_DIR, settings.LOGS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
