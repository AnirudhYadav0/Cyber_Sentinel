import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CyberSentinel API"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    # CORS origins: configured for the actual local Next.js frontend origin
    cors_origins: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # MongoDB placeholders (not connected in Phase 1)
    mongodb_uri: str = "mongodb_connection_string_placeholder"
    mongodb_database: str = "cybersentinel"

    # Demo Mode
    demo_mode: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
