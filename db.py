from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.8-27b:free"
    typesafe_api_key: str = ""
    database_url: str = "sqlite:///./data/papers.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if settings.database_url.startswith("sqlite:///./"):
    Path("./data").mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
