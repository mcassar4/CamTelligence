from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ct_core.models import Notification, PersonEvent, VehicleEvent

from ..dependencies import db_dep

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/metrics")
def metrics(db: Session = Depends(db_dep)) -> dict:
    return {
        "persons": db.query(PersonEvent).count(),
        "vehicles": db.query(VehicleEvent).count(),
        "notifications": db.query(Notification).count(),
    }
