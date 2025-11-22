from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from ct_core.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_dep(dep: Session = Depends(get_db)) -> Session:
    return dep
