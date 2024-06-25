from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TOKEN: str
    OPENAI_API_KEY: str
    ASSISTANT_ID: str

    class Config:
        env_file = ".env"


settings = Settings()
