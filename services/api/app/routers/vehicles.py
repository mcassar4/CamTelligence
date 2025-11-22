from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ct_core.schemas import VehicleEventSchema

from ..dependencies import db_dep
from ..services.event_service import EventService
router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/recent", response_model=list[VehicleEventSchema])
def recent_vehicles(db: Session = Depends(db_dep), limit: int = 25):
    service = EventService(db)
    return service.recent_vehicles(limit)
