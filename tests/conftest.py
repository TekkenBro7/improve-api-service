import asyncio
from typing import AsyncGenerator, Callable, Generator

import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import postgres_config
from src.database.base import Base
from src.database.session import get_async_session
from src.main import app


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an instance of the default event loop for the session.
    Needed for session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Creates and deliver an asynchronous engine for the entire test session
    """
    engine = create_async_engine(postgres_config.async_test_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_db(test_async_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Creates tables before tests and deletes them after all tests
    """
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session(
    test_async_engine: AsyncEngine, setup_db: None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a new asynchronous SQLAlchemy session for each test with transaction isolation
    """
    connection = await test_async_engine.connect()
    transaction = await connection.begin()

    test_async_session_maker = async_sessionmaker(
        connection, expire_on_commit=False, class_=AsyncSession
    )

    async with test_async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await connection.close()


@pytest_asyncio.fixture
def override_get_db(
    db_session: AsyncSession,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """
    Override for the get_async_session dependency FastAPI
    """

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    return _override_get_db


@pytest_asyncio.fixture
def overridden_app(
    override_get_db: Callable[[], AsyncGenerator[AsyncSession, None]],
) -> Generator[FastAPI, None, None]:
    """
    FastAPI application with substituted dependency get_async_session.
    """
    app.dependency_overrides[get_async_session] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(overridden_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create a test client for making HTTP requests to the FastAPI application.
    """
    async with AsyncClient(app=overridden_app, base_url="http://test") as ac:
        yield ac
