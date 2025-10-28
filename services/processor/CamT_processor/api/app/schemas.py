from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from oi_core.schemas import PersonEventSchema, VehicleEventSchema


class SettingsUpdate(BaseModel):
    key: str
    value: dict


class EventFilter(BaseModel):
    camera: Optional[str] = None
    event_type: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = 50


class EventResponse(BaseModel):
    person_events: List[PersonEventSchema]
    vehicle_events: List[VehicleEventSchema]
