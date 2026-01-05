from pydantic import BaseSettings

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "gpt-4o-mini"
    DB_PATH: str = "./data/context.db"
    ADMIN_CHAT_ID: str | None = None
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
