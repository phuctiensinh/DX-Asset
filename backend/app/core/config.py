from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    APP_NAME: str = "DX-Asset"
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production-super-secret-key-32bytes"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql://dx_user:dx_password_secret@localhost:5432/dx_asset_db"

    # CORS Origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # AI Feature
    AI_ENABLED: bool = True
    AI_API_KEY: Optional[str] = None
    AI_API_URL: str = "https://api.openai.com/v1"

    # Keycloak OIDC Settings
    KEYCLOAK_ENABLED: bool = True
    KEYCLOAK_ISSUER_URL: str = "http://localhost:8080/realms/dx-asset"
    KEYCLOAK_JWKS_URL: str = "http://localhost:8080/realms/dx-asset/protocol/openid-connect/certs"
    KEYCLOAK_CLIENT_ID: str = "dx-asset-frontend"

    # SeaweedFS Attachment Storage
    SEAWEEDFS_FILER_URL: str = "http://localhost:8888"
    MAX_UPLOAD_SIZE_MB: int = 10


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
