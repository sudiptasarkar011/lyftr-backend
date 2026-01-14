from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    app_name: str = "Lyftr Webhook API"
    webhook_secret: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    log_level: str = "INFO"

settings = Settings()