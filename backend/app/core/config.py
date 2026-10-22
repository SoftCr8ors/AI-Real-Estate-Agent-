from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory path (3 levels up from config.py)
# config.py location: backend/app/core/config.py
# We want: backend/.env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

# Debug: Print the .env path
print(f"🔍 Looking for .env at: {ENV_FILE}")
print(f"🔍 .env exists: {ENV_FILE.exists()}")


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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()

# Debug: Print what was actually loaded
print(f"🔍 AI_PROVIDER loaded: {settings.AI_PROVIDER}")
print(f"🔍 GEMINI_API_KEY loaded: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
print(f"🔍 GROQ_API_KEY loaded: {'Yes' if settings.GROQ_API_KEY else 'No'}")
print(f"🔍 ENCRYPTION_KEY loaded: {'Yes' if settings.ENCRYPTION_KEY else 'No'}")
