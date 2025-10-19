from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from oi_core.models import PersonEvent, VehicleEvent


class EventRepository:
    def __init__(self, session: Session):
        self.session = session

    def recent_persons(self, limit: int = 25) -> List[PersonEvent]:
        return (
            self.session.query(PersonEvent)
            .order_by(PersonEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )

    def recent_vehicles(self, limit: int = 25) -> List[VehicleEvent]:
        return (
            self.session.query(VehicleEvent)
            .order_by(VehicleEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )

    def filter_events(
        self,
        camera: Optional[str] = None,
        event_type: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 50,
    ) -> tuple[list[PersonEvent], list[VehicleEvent]]:
        filters = []
        if camera:
            filters.append(
                (
                    PersonEvent.camera == camera,
                    VehicleEvent.camera == camera,
                )
            )
        if start:
            filters.append(
                (
                    PersonEvent.occurred_at >= start,
                    VehicleEvent.occurred_at >= start,
                )
            )
        if end:
            filters.append(
                (
                    PersonEvent.occurred_at <= end,
                    VehicleEvent.occurred_at <= end,
                )
            )

        person_query = self.session.query(PersonEvent)
        vehicle_query = self.session.query(VehicleEvent)
        for f_person, f_vehicle in filters:
            person_query = person_query.filter(f_person)
            vehicle_query = vehicle_query.filter(f_vehicle)

        if event_type == "person":
            return person_query.order_by(PersonEvent.occurred_at.desc()).limit(limit).all(), []
        if event_type == "vehicle":
            return [], vehicle_query.order_by(VehicleEvent.occurred_at.desc()).limit(limit).all()

        persons = person_query.order_by(PersonEvent.occurred_at.desc()).limit(limit).all()
        vehicles = vehicle_query.order_by(VehicleEvent.occurred_at.desc()).limit(limit).all()
        return persons, vehicles
