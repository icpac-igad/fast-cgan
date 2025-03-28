from collections.abc import AsyncGenerator, Callable
from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import Any

import anyio
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from fastcgan.middleware.client_cache_middleware import ClientCacheMiddleware
from fastcgan.routes import limiter
from fastcgan.tools.config import (
    AppSettings,
    AssetPathSettings,
    ClientSideCacheSettings,
    EnvironmentOption,
    EnvironmentSettings,
    OpenapiSettings,
    RedisCacheSettings,
    RedisQueueSettings,
    RedisRateLimiterSettings,
    get_cached_file_base_path,
    settings,
)
from fastcgan.utils import cache, queue, rate_limit

# -------------- database --------------
# async def create_tables() -> None:
#     async with engine().begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


# -------------- cache --------------
async def create_redis_cache_pool() -> None:
    cache.pool = redis.ConnectionPool.from_url(settings.REDIS_CACHE_URL)
    cache.client = redis.Redis.from_pool(cache.pool)  # type: ignore


async def close_redis_cache_pool() -> None:
    await cache.client.aclose()  # type: ignore


# -------------- queue --------------
async def create_redis_queue_pool() -> None:
    queue.pool = await create_pool(RedisSettings(host=settings.REDIS_QUEUE_HOST, port=settings.REDIS_QUEUE_PORT))


async def close_redis_queue_pool() -> None:
    await queue.pool.aclose()  # type: ignore


# -------------- rate limit --------------
async def create_redis_rate_limit_pool() -> None:
    rate_limit.pool = redis.ConnectionPool.from_url(settings.REDIS_RATE_LIMIT_URL)
    rate_limit.client = redis.Redis.from_pool(rate_limit.pool)  # type: ignore


async def close_redis_rate_limit_pool() -> None:
    await rate_limit.client.aclose()  # type: ignore


# -------------- application --------------
async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = number_of_tokens


def lifespan_factory(
    settings: (RedisCacheSettings | AppSettings | ClientSideCacheSettings | RedisQueueSettings | RedisRateLimiterSettings | EnvironmentSettings),
) -> Callable[[FastAPI], _AsyncGeneratorContextManager[Any]]:
    """Factory to create a lifespan async context manager for a FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        await set_threadpool_tokens()

        if isinstance(settings, RedisCacheSettings):
            await create_redis_cache_pool()

        if isinstance(settings, RedisQueueSettings):
            await create_redis_queue_pool()

        if isinstance(settings, RedisRateLimiterSettings):
            await create_redis_rate_limit_pool()

        yield

        if isinstance(settings, RedisCacheSettings):
            await close_redis_cache_pool()

        if isinstance(settings, RedisQueueSettings):
            await close_redis_queue_pool()

        if isinstance(settings, RedisRateLimiterSettings):
            await close_redis_rate_limit_pool()

    return lifespan


# -------------- application --------------
def create_application(
    settings: (
        AppSettings
        | OpenapiSettings
        | RedisCacheSettings
        | RedisQueueSettings
        | RedisRateLimiterSettings
        | ClientSideCacheSettings
        | EnvironmentSettings
    ),
    **kwargs: Any,
) -> FastAPI:
    """Creates and configures a FastAPI application based on the provided settings.

    This function initializes a FastAPI application and configures it with various settings
    and handlers based on the type of the `settings` object provided.

    Parameters
    ----------
    router : APIRouter
        The APIRouter object containing the routes to be included in the FastAPI application.

    settings
        An instance representing the settings for configuring the FastAPI application.
        It determines the configuration applied:

        - AppSettings: Configures basic app metadata like name, description, contact, and license info.
        - DatabaseSettings: Adds event handlers for initializing database tables during startup.
        - RedisCacheSettings: Sets up event handlers for creating and closing a Redis cache pool.
        - ClientSideCacheSettings: Integrates middleware for client-side caching.
        - RedisQueueSettings: Sets up event handlers for creating and closing a Redis queue pool.
        - RedisRateLimiterSettings: Sets up event handlers for creating and closing a Redis rate limiter pool.
        - EnvironmentSettings: Conditionally sets documentation URLs and integrates custom routes for API documentation
          based on the environment type.

    create_tables_on_start : bool
        A flag to indicate whether to create database tables on application startup.
        Defaults to True.

    **kwargs
        Additional keyword arguments passed directly to the FastAPI constructor.

    Returns
    -------
    FastAPI
        A fully configured FastAPI application instance.

    The function configures the FastAPI application with different features and behaviors
    based on the provided settings. It includes setting up database connections, Redis pools
    for caching, queue, and rate limiting, client-side caching, and customizing the API documentation
    based on the environment settings.
    """
    # --- before creating application ---
    if isinstance(settings, AppSettings):
        to_update = {
            "title": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "contact": {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL},
            "license_info": {"name": settings.LICENSE_NAME},
        }
        kwargs.update(to_update)

    if isinstance(settings, OpenapiSettings):
        kwargs.update(
            {
                "docs_url": settings.DOCS_URL,
                "redoc_url": settings.REDOC_URL,
                "openapi_url": settings.OPENAPI_URL,
            }
        )

    lifespan = lifespan_factory(settings)

    application = FastAPI(lifespan=lifespan, **kwargs)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)

    if isinstance(settings, ClientSideCacheSettings):
        application.add_middleware(ClientCacheMiddleware, max_age=settings.CLIENT_CACHE_MAX_AGE)

    if isinstance(settings, AssetPathSettings):
        if settings.ENVIRONMENT != EnvironmentOption.PRODUCTION:
            # mount media files
            application.mount(
                settings.CACHE_BASE_URL,
                StaticFiles(directory=get_cached_file_base_path("media")),
                name="media",
            )

    return application
