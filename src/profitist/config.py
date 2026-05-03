from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required
    telegram_bot_token: str
    openai_api_key: str = Field(
        validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY", "anthropic_api_key", "ANTHROPIC_API_KEY")
    )
    telegram_chat_id: int
    database_url: str

    # Optional
    api_base_url: str = "https://api.aitunnel.ru/v1/"
    tavily_api_key: str = ""

    main_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"

    max_working_memory_turns: int = 8
    proactive_check_hour: int = 9
    summarize_interval_hours: int = 6
    summarize_min_messages: int = 10
    summarize_older_than_hours: int = 24
    max_relevant_episodes: int = 3

    log_level: str = "INFO"


settings = Settings()
