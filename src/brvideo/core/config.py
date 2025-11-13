import os
from pathlib import Path
from typing import List, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env",
        env_nested_delimiter="__",
        extra="allow",  # bruh
    )

    TOKEN: str
    OWNERS: List[int]
    DATABASE_URL: str
    APPLICATIONS_CHAT_ID: int
    APPLICATIONS_THREAD_ID: Optional[int] = None

    @model_validator(mode="before")
    def parse_empty_string_to_none(cls, values):
        for key, val in values.items():
            if val == "":
                values[key] = None
        return values


settings = Settings()  # type: ignore

database_config = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": [
                f"{'' if os.getcwd().endswith('src') else 'src.'}brvideo.core.models",
                "aerich.models",
            ],
            "default_connection": "default",
        },
    },
}
