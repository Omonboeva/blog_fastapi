from pydantic_settings import BaseSettings
from pydantic import AnyUrl


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:123@localhost:5432/blog_db"
    SECRET_KEY: str = "59c48aaad8fb52387fd9bf562cc9edb1ff50660578fcf19c0b891d7178017f43"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()