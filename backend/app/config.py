import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "RecoverAI"
    PROJECT_NAME: str = "RecoverAI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS Settings
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database Configuration (Defaults to SQLite for simple local execution, supports PostgreSQL)
    DATABASE_URL: str = "sqlite:///./recoverai.db"

    # Razorpay Credentials (Populated in Phase 7)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # AI Configuration
    LLM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
