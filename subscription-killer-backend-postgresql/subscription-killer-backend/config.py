import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/subscription_killer"
    )
    APP_MODE = os.getenv("APP_MODE", "demo")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "1") == "1"
    BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID", "")
    BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY", "")
    BHASHINI_PIPELINE_ID = os.getenv("BHASHINI_PIPELINE_ID", "")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
