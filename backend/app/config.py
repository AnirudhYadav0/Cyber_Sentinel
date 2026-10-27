import os
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET_PLACEHOLDER = "cybersentinel-development-secret-key-32bytes-min!"


class Settings(BaseSettings):
    app_name: str = "CyberSentinel API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    # CORS origins: configured for the actual frontend origin
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # MongoDB Atlas settings
    mongodb_uri: str = "mongodb_connection_string_placeholder"
    mongodb_database: str = "cybersentinel"
    mongodb_timeout_ms: int = 5000

    # Demo Mode
    demo_mode: bool = True

    # Security & Authentication
    jwt_secret_key: str = DEV_JWT_SECRET_PLACEHOLDER
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    auth_required: bool = True

    # Initial default credentials (used to seed development accounts)
    admin_default_username: str = "admin"
    admin_default_password: str = "CyberSentinel#Admin2026!"
    analyst_default_username: str = "analyst"
    analyst_default_password: str = "CyberSentinel#Analyst2026!"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 15

    # Request Size Limits
    max_request_body_bytes: int = 15 * 1024 * 1024  # 15 MB
    max_upload_size_bytes: int = 10 * 1024 * 1024   # 10 MB

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_configuration(self):
        """Enforce strict configuration hygiene when operating in production."""
        if self.app_env.lower() == "production":
            # 1. Require strong, non-default JWT secret
            if self.jwt_secret_key == DEV_JWT_SECRET_PLACEHOLDER or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production environment, "
                    "JWT_SECRET_KEY must be explicitly set in environment variables to a cryptographically "
                    "strong key of at least 32 characters."
                )

            # 2. Require real MongoDB URI
            if (
                not self.mongodb_uri
                or self.mongodb_uri == "mongodb_connection_string_placeholder"
                or "placeholder" in self.mongodb_uri
            ):
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: In production environment, "
                    "MONGODB_URI must be configured with a valid MongoDB connection string."
                )

            # 3. Disallow wildcard CORS in production
            if "*" in self.cors_origins:
                raise ValueError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: Wildcard '*' CORS origin is not permitted in production."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
