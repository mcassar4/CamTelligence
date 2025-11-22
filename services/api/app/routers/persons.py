from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ct_core.schemas import PersonEventSchema

from ..dependencies import db_dep
from ..services.event_service import EventService

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("/recent", response_model=list[PersonEventSchema])
def recent_persons(db: Session = Depends(db_dep), limit: int = 25):
    service = EventService(db)
    return service.recent_persons(limit)
