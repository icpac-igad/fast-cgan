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
    APP_NAME: str = config(
        "APP_NAME", default="Weather and Climate Forecast Systems API"
    )
    APP_DESCRIPTION: str | None = config(
        "APP_DESCRIPTION",
        default="API gateway for the Strengthening Early Warning Systems for Anticipatory Action (SEWAA) Project",
    )
    APP_VERSION: str | None = config("APP_VERSION", default="0.1")
    APP_BASE_URL: str | None = config("BASE_URL", default="http://127.0.0.1:8000")
    APP_SUBPATH: str | None = config("SUB_PATH", default="")
    APP_DUMPS_DIR: str | None = os.path.expandvars(
        config("DUMPS_DIR", default=os.path.join(base_dir, "dumps"))
    )
    ALLOWED_ORIGINS: str | None = config(
        "ALLOWED_ORIGINS", default="https://cgan.icpac.net,http://localhost:5173"
    )
    LICENSE_NAME: str | None = config("LICENSE", default="CC BY 4.0")
    CONTACT_NAME: str | None = config("CONTACT_NAME", default="Developer")
    CONTACT_EMAIL: str | None = config("CONTACT_EMAIL", default="developer@icpac.net")
    MASK_REGION: str | None = config("MASK_REGION", default="East Africa")
    USE_UI_FS: bool | None = config("USE_UI_FS", default=True)


class AssetPathSettings(BaseSettings):
    CACHE_FILES_DIR: str | None = os.path.expandvars(
        config("CACHE_DIR", default=os.path.join(base_dir, "cache"))
    )
    FORECASTS_DATA_DIR: str | None = os.path.expandvars(
        config("FORECASTS_DATA_DIR", default=os.path.join(base_dir, "./data"))
    )
    JOBS_DATA_DIR: str | None = os.path.expandvars(
        config("JOBS_DATA_DIR", default=os.path.join(base_dir, "./jobs"))
    )
    ASSETS_DIR_MAP: dict[str, str] = {
        "cache": CACHE_FILES_DIR,
        "jobs": JOBS_DATA_DIR,
        "forecasts": FORECASTS_DATA_DIR,
    }
    CACHE_BASE_URL: str | None = os.path.expandvars(
        config("CACHE_URL", default="/media")
    )


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
    POSTGRES_ASYNC_PREFIX: str = config(
        "POSTGRES_ASYNC_PREFIX", default="postgresql+asyncpg://"
    )
    POSTGRES_URI: str = os.path.expandvars(
        config(
            "POSTGRES_URI",
            default=f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}",
        )
    )


class RedisCacheSettings(BaseSettings):
    REDIS_CACHE_HOST: str = os.path.expandvars(
        config("REDIS_CACHE_HOST", default="localhost")
    )
    REDIS_CACHE_PORT: int = os.path.expandvars(config("REDIS_CACHE_PORT", default=6379))
    REDIS_CACHE_URL: str = f"redis://{REDIS_CACHE_HOST}:{REDIS_CACHE_PORT}"


class ClientSideCacheSettings(BaseSettings):
    CLIENT_CACHE_MAX_AGE: int = config("CLIENT_CACHE_MAX_AGE", default=60)


class RedisQueueSettings(BaseSettings):
    REDIS_QUEUE_HOST: str = os.path.expandvars(
        config("REDIS_QUEUE_HOST", default="localhost")
    )
    REDIS_QUEUE_PORT: int = config("REDIS_QUEUE_PORT", default=6379)


class RedisRateLimiterSettings(BaseSettings):
    REDIS_RATE_LIMIT_HOST: str = os.path.expandvars(
        config("REDIS_RATE_LIMIT_HOST", default="localhost")
    )
    REDIS_RATE_LIMIT_PORT: int = config("REDIS_RATE_LIMIT_PORT", default=6379)
    REDIS_RATE_LIMIT_DATABASE: int = config("REDIS_RATE_LIMIT_DATABASE", default=10)
    REDIS_RATE_LIMIT_URL: str = (
        f"redis://{REDIS_RATE_LIMIT_HOST}:{REDIS_RATE_LIMIT_PORT}/{REDIS_RATE_LIMIT_DATABASE}"
    )


class DefaultRateLimitSettings(BaseSettings):
    DEFAULT_RATE_LIMIT_LIMIT: int = config("DEFAULT_RATE_LIMIT_LIMIT", default=10)
    DEFAULT_RATE_LIMIT_PERIOD: int = config("DEFAULT_RATE_LIMIT_PERIOD", default=3600)


class EnvironmentOption(Enum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: EnvironmentOption = config("ENVIRONMENT", default="production")


class Settings(
    AppSettings,
    AssetPathSettings,
    PostgresSettings,
    CryptSettings,
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


def get_asset_dir_path(asset: Literal["cache"]) -> Path:
    asset_path = Path(settings.ASSETS_DIR_MAP[asset])
    if not asset_path.exists():
        asset_path.mkdir(parents=True)
    return asset_path


def get_cached_file_base_path(
    file_type: Literal["media", "data"] | None = "media", source: str | None = None
) -> Path:
    cache_path = get_asset_dir_path("cache") / file_type
    if source is not None:
        cache_path = cache_path / source
    if not cache_path.exists():
        cache_path.mkdir(parents=True)
    return cache_path


def get_cached_file_url(file_path: str | Path) -> str:
    media_path = str(file_path).replace(
        f"{settings.ASSETS_DIR_MAP['cache']}/media/", ""
    )
    return f"{settings.APP_BASE_URL}{settings.APP_SUBPATH}{settings.CACHE_BASE_URL}/{media_path}"


def get_allowed_cor_origins() -> list[str]:
    return settings.ALLOWED_ORIGINS.split(",")
