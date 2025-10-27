from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..dependencies import db_dep
from ..schemas import EventFilter, EventResponse
from ..services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/filter", response_model=EventResponse)
def filter_events(payload: EventFilter, db: Session = Depends(db_dep)):
    service = EventService(db)
    persons, vehicles = service.filter_events(
        camera=payload.camera,
        event_type=payload.event_type,
        start=payload.start,
        end=payload.end,
        limit=payload.limit,
    )
    return {"person_events": persons, "vehicle_events": vehicles}
