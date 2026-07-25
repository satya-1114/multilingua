from __future__ import annotations

import os

# Use PostgreSQL by default for tests. GitHub Actions can override these
# environment variables if needed.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://platform:platform@localhost:5432/platform",
)
os.environ.setdefault(
    "DATABASE_URL_ASYNC",
    "postgresql+asyncpg://platform:platform@localhost:5432/platform",
)
os.environ.setdefault(
    "APP_SECRET_KEY",
    "test-secret-that-is-long-enough",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.security.rate_limit import default_limiter, _policies
from app.database.session import engine
from app.dependencies.db import get_db
from main import app

from sqlalchemy import text


@pytest.fixture(scope="session")
def test_engine():
    """
    Use the application's SQLAlchemy engine.

    Database schema must already exist.
    GitHub Actions will execute:

        alembic upgrade head

    before pytest starts.
    """
    yield engine


@pytest.fixture(autouse=True)
def auth_test_settings(monkeypatch):
    """
    Prevent auth rate limiting from interfering with account-lockout tests.
    """
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 100)

    # Rebuild cached policies
    default_limiter.policies = _policies()

    # Reset limiter state
    default_limiter.store.reset()

    yield

    # Restore policies and clear state
    default_limiter.policies = _policies()
    default_limiter.store.reset()   

@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

    session = Session()

    try:
        yield session
    finally:
        session.close()

        with test_engine.begin() as conn:
            tables = conn.execute(text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> 'alembic_version'
            """)).scalars().all()

            if tables:
                quoted = ", ".join(f'"{t}"' for t in tables)
                conn.execute(
                    text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
                )


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()