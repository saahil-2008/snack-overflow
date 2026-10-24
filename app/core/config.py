# app/core/config.py — centralised configuration from environment variables
import os


DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./farmpool.db")
JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-only-change-me-at-least-32chars!")
FRONTEND_BASE_URL: str = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")
CORS_EXTRA_ORIGINS: str = os.environ.get("CORS_EXTRA_ORIGINS", "")
AUDIO_DIR: str = os.environ.get("AUDIO_DIR", "./data/audio")
SEED_DEMO: bool = os.environ.get("SEED_DEMO", "true").lower() in ("true", "1", "yes")
ENV: str = os.environ.get("ENV", "dev")
CONTRACT_VERSION: str = "1.1.0"
