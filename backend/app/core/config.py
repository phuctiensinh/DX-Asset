from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "DX-Asset"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production-super-secret-key-32bytes"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql://dx_user:dx_password_secret@localhost:5432/dx_asset_db"

    # AI Feature
    AI_ENABLED: bool = True
    AI_API_KEY: Optional[str] = None
    AI_API_URL: str = "https://api.openai.com/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
