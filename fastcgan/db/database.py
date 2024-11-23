# database connections management module
# read https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308

import json

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, sessionmaker

from fastcgan.config import EnvironmentOption, settings


def custom_json_serializer(d):
    return json.loads(json.dumps(d, default=lambda v: v.json()))


class Base(DeclarativeBase, MappedAsDataclass):
    pass


def create_sync_sa_engine():
    DEBUG = True if settings.ENVIRONMENT in [EnvironmentOption.LOCAL, EnvironmentOption.STAGING] else False
    return create_engine(f"{settings.POSTGRES_SYNC_PREFIX}{settings.POSTGRES_URI}", echo=DEBUG)


def async_db_engine():
    DEBUG = True if settings.ENVIRONMENT in [EnvironmentOption.LOCAL, EnvironmentOption.STAGING] else False
    return create_async_engine(
        f"{settings.POSTGRES_ASYNC_PREFIX}{settings.POSTGRES_URI}",
        isolation_level="SERIALIZABLE",
        json_serializer=custom_json_serializer,
        echo=DEBUG,
        hide_parameters=not DEBUG,
        future=True,
    )


async def get_connectable_session() -> sessionmaker:
    return sessionmaker(
        bind=async_db_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        # autocommit=False,
        # autoflush=False,
        # future=True,
    )


async def get_async_session() -> AsyncSession:
    sessionmaker = await get_connectable_session()
    return sessionmaker()


# check the following links for more details
# https://github.com/tiangolo/fastapi/discussions/8443
# https://github.com/pandas-dev/pandas/issues/51633
# https://github.com/sqlalchemy/sqlalchemy/discussions/7634
async def get_async_db_session():
    async_session = await get_connectable_session()
    async with async_session() as session:
        try:
            yield session
        except Exception as err:
            await session.rollback()
            raise err
        finally:
            await session.close()
