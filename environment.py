from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TOKEN: str
    OPENAI_API_KEY: str
    ASSISTANT_ID: str
    DATABASE_URL: str
    model_config = SettingsConfigDict(env_file='.env')
