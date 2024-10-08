from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TOKEN: str
    OPENAI_API_KEY: str
    AMPLITUDE_API_KEY: str
    ASSISTANT_ID: str
    DATABASE_URL: str
    NOTION_TOKEN: str
    NOTION_DB_ID: str
    NOTION_DOMAIN: str
    model_config = SettingsConfigDict(env_file='.env')
