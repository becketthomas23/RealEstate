"""SQLAlchemy setup with SQLite for local development and PostgreSQL in production."""

import os
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


DEFAULT_DATABASE_URL = "sqlite:///./cre_underwriting.db"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _normalize_database_url(url: str) -> str:
    """Accept managed-host PostgreSQL URLs while selecting the installed driver."""
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if "supabase.com" in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}sslmode=require"
    return url


def _escape_alembic_config_value(value: str) -> str:
    """Escape percent signs for Alembic's ConfigParser interpolation.

    URL-encoded database passwords can contain percent signs (for example,
    ``%24`` for ``$``). SQLAlchemy needs the original URL, but ConfigParser
    requires each percent sign to be doubled when setting a value.
    """
    return value.replace("%", "%%")


class Database:
    """Own the database engine and sessions used by the HTTP application."""

    def __init__(self, url: str | None = None) -> None:
        self.url = _normalize_database_url(url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
        connect_args = {"check_same_thread": False} if self.url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(self.url, connect_args=connect_args, pool_pre_ping=True)
        self._sessions = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    def upgrade_schema(self) -> None:
        """Apply every versioned schema migration before serving requests.

        A developer database created before migrations were introduced is stamped
        at the initial revision only when all current application tables already
        exist. New databases always receive the migration's DDL.
        """
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", _escape_alembic_config_value(self.url))
        existing_tables = set(inspect(self.engine).get_table_names())
        application_tables = set(Base.metadata.tables)
        if application_tables.issubset(existing_tables) and "alembic_version" not in existing_tables:
            command.stamp(config, "head")
            return
        command.upgrade(config, "head")

    def create_schema(self) -> None:
        """Create the local schema without requiring migration files."""
        Base.metadata.create_all(self.engine)

    def session(self) -> Generator[Session, None, None]:
        session = self._sessions()
        try:
            yield session
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
