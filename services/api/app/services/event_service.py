from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from oi_core.models import PersonEvent, VehicleEvent

from ..repositories.event_repository import EventRepository


class EventService:
    def __init__(self, session: Session):
        self.repo = EventRepository(session)

    def recent_persons(self, limit: int = 25) -> List[PersonEvent]:
        return self.repo.recent_persons(limit)

    def recent_vehicles(self, limit: int = 25) -> List[VehicleEvent]:
        return self.repo.recent_vehicles(limit)

    def filter_events(
        self,
        camera: Optional[str],
        event_type: Optional[str],
        start: Optional[datetime],
        end: Optional[datetime],
        limit: int = 50,
    ) -> Tuple[List[PersonEvent], List[VehicleEvent]]:
        return self.repo.filter_events(camera, event_type, start, end, limit)
