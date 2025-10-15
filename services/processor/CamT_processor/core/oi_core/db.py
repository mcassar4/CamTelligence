from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_db_settings
from .models import Base

settings = get_db_settings()

engine = create_engine(
    settings.db_uri,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    # For production we rely on Alembic migrations; fall back to metadata
    # creation when using in-memory SQLite (tests) so that schemas exist.
    if engine.url.get_backend_name().startswith("sqlite"):
        Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
