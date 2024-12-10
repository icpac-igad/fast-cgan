import os
from enum import Enum
from json import loads
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from starlette.config import Config

current_file_dir = os.path.dirname(os.path.realpath(__file__))
base_dir = os.path.abspath(f"{current_file_dir}/../../")
env_path = os.path.join(base_dir, ".env")
config = Config(env_path)


class AppSettings(BaseSettings):
    APP_NAME: str = config("APP_NAME", default="FastAPI app")
    APP_DESCRIPTION: str | None = config("APP_DESCRIPTION", default=None)
    APP_VERSION: str | None = config("APP_VERSION", default=None)
    APP_BASE_URL: str | None = config("BASE_URL", default="http://127.0.0.1:8000")
    APP_DUMPS_DIR: str | None = config("DUMPS_DIR", default=os.path.join(base_dir, "dumps"))
    ALLOWED_ORIGINS: str | None = config("ALLOWED_ORIGINS", default="https://cgan.icpac.net,http://localhost:5173")
    LICENSE_NAME: str | None = config("LICENSE", default=None)
    CONTACT_NAME: str | None = config("CONTACT_NAME", default=None)
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default=None)
    MASK_REGION: str | None = config("MASK_REGION", default=None)


class AssetPathSettings(BaseSettings):
    STATIC_ASSETS_DIR: str | None = config("STATIC_DIR", default=os.path.join(base_dir, "static"))
    CACHE_FILES_DIR: str | None = config("CACHE_DIR", default=os.path.join(base_dir, "cache"))
    APP_DATA_DIR: str | None = config("APP_DATA_DIR", default=os.path.join(base_dir, "data"))
    IFS_DATA_DIR: str | None = config("IFS_DIR", default=os.path.join(APP_DATA_DIR, "open-ifs"))
    GAN_DATA_DIR: str | None = config("GAN_DIR", default=os.path.join(APP_DATA_DIR, "cgan"))
    ASSETS_DIR_MAP: dict[str, str] = {
        "static": STATIC_ASSETS_DIR,
        "cache": CACHE_FILES_DIR,
        "forecasts": APP_DATA_DIR,
        "cgan": GAN_DATA_DIR,
        "open_ifs": IFS_DATA_DIR,
    }
    STATIC_BASE_URL: str | None = config("STATIC_URL", default="/static")
    CACHE_BASE_URL: str | None = config("CACHE_URL", default="/media")


class CryptSettings(BaseSettings):
    SECRET_KEY: str = config("SECRET_KEY")
    ALGORITHM: str = config("ALGORITHM", default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = config("REFRESH_TOKEN_EXPIRE_DAYS", default=7)


class PostgresSettings(BaseSettings):
    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="postgres")
    POSTGRES_SERVER: str = config("POSTGRES_SERVER", default="localhost")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432)
    POSTGRES_DB: str = config("POSTGRES_DB", default="postgres")
    POSTGRES_SYNC_PREFIX: str = config("POSTGRES_SYNC_PREFIX", default="postgresql://")
    POSTGRES_ASYNC_PREFIX: str = config("POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://")
    POSTGRES_URI: str = f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    POSTGRES_URL: str | None = config("POSTGRES_URL", default=None)


class FirstUserSettings(BaseSettings):
    ADMIN_NAME: str = config("ADMIN_NAME", default="admin")
    ADMIN_EMAIL: str = config("ADMIN_EMAIL", default="admin@admin.com")
    ADMIN_USERNAME: str = config("ADMIN_USERNAME", default="admin")
    ADMIN_PASSWORD: str = config("ADMIN_PASSWORD", default="!Ch4ng3Th1sP4ssW0rd!")


class TestSettings(BaseSettings): ...


class RedisCacheSettings(BaseSettings):
    REDIS_CACHE_HOST: str = config("REDIS_CACHE_HOST", default="localhost")
    REDIS_CACHE_PORT: int = config("REDIS_CACHE_PORT", default=6379)
    REDIS_CACHE_URL: str = f"redis://{REDIS_CACHE_HOST}:{REDIS_CACHE_PORT}"


class ClientSideCacheSettings(BaseSettings):
    CLIENT_CACHE_MAX_AGE: int = config("CLIENT_CACHE_MAX_AGE", default=60)


class RedisQueueSettings(BaseSettings):
    REDIS_QUEUE_HOST: str = config("REDIS_QUEUE_HOST", default="localhost")
    REDIS_QUEUE_PORT: int = config("REDIS_QUEUE_PORT", default=6379)


class RedisRateLimiterSettings(BaseSettings):
    REDIS_RATE_LIMIT_HOST: str = config("REDIS_RATE_LIMIT_HOST", default="localhost")
    REDIS_RATE_LIMIT_PORT: int = config("REDIS_RATE_LIMIT_PORT", default=6379)
    REDIS_RATE_LIMIT_DATABASE: int = config("REDIS_RATE_LIMIT_DATABASE", default=10)
    REDIS_RATE_LIMIT_URL: str = f"redis://{REDIS_RATE_LIMIT_HOST}:{REDIS_RATE_LIMIT_PORT}/{REDIS_RATE_LIMIT_DATABASE}"


class DefaultRateLimitSettings(BaseSettings):
    DEFAULT_RATE_LIMIT_LIMIT: int = config("DEFAULT_RATE_LIMIT_LIMIT", default=10)
    DEFAULT_RATE_LIMIT_PERIOD: int = config("DEFAULT_RATE_LIMIT_PERIOD", default=3600)


class EnvironmentOption(Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = config("ENVIRONMENT", default="local")


class Settings(
    AppSettings,
    AssetPathSettings,
    PostgresSettings,
    CryptSettings,
    FirstUserSettings,
    TestSettings,
    RedisCacheSettings,
    ClientSideCacheSettings,
    RedisQueueSettings,
    RedisRateLimiterSettings,
    DefaultRateLimitSettings,
    EnvironmentSettings,
):
    pass


settings = Settings()


def get_major_towns_data():
    with open(f"{settings.APP_DUMPS_DIR}/ea-major-towns.json") as dp:
        return loads(dp.read())


def get_asset_dir_path(asset: Literal["static", "cache"]) -> Path:
    asset_path = Path(settings.ASSETS_DIR_MAP[asset])
    if not asset_path.exists():
        asset_path.mkdir(parents=True)
    return asset_path


def get_cached_file_base_path(file_type: Literal["media", "data"] | None = "media") -> Path:
    cache_path = get_asset_dir_path("cache") / file_type
    if not cache_path.exists():
        cache_path.mkdir(parents=True)
    return cache_path


def get_cached_file_url(file_path: str | Path) -> str:
    media_path = str(file_path).replace(f"{settings.ASSETS_DIR_MAP['cache']}/media/", "")
    return f"{settings.APP_BASE_URL}{settings.CACHE_BASE_URL}/{media_path}"


def get_allowed_cor_origins() -> list[str]:
    return settings.ALLOWED_ORIGINS.split(",")
