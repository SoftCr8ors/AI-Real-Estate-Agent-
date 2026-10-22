from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory path (3 levels up from config.py)
# config.py location: backend/app/core/config.py
# We want: backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_prefix="",
    )

    # Application
    APP_NAME: str = "AI Real Estate Agent"
    DEBUG: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql://realestate:realestate@localhost:5432/realestate"

    # Phase 4: AI Provider Configuration
    AI_PROVIDER: str = "gemini"  # Default provider: gemini, groq, or openai

    # Phase 4: AI Provider API Keys (optional - can be set in admin settings too)
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    # Phase 4: Encryption key for storing sensitive settings
    ENCRYPTION_KEY: str | None = None

    # Phase 5: Google Calendar Integration
    GOOGLE_SERVICE_ACCOUNT_FILE: str | None = None  # Path to service account JSON key file
    GOOGLE_CALENDAR_ID: str | None = None  # Sales agent's calendar ID (email address)
    GOOGLE_CALENDAR_TIMEZONE: str = "Asia/Dubai"  # Default timezone for appointments
    GOOGLE_CALENDAR_RETRY_MAX: int = 3  # Max retries for failed sync
    GOOGLE_CALENDAR_RETRY_DELAY: int = 300  # Seconds between retries (5 minutes)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
