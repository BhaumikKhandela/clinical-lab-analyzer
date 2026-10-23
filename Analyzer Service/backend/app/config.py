import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "groq")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


settings = Settings()
