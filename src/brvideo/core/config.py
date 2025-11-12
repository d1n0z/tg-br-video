from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env", env_nested_delimiter="__", extra="allow"
    )

    TOKEN: str
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
            "models": ["brvideo.core.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
