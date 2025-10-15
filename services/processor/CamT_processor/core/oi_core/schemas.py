from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from .models import EventType, JobStatus, MediaType, NotificationStatus


class MediaAssetSchema(BaseModel):
    id: UUID
    media_type: MediaType
    path: str
    attributes: Optional[dict]
    created_at: datetime

    class Config:
        orm_mode = True


class PersonEventSchema(BaseModel):
    id: UUID
    camera: str
    occurred_at: datetime
    frame_asset: Optional[MediaAssetSchema]
    crop_asset: Optional[MediaAssetSchema]
    score: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class VehicleEventSchema(BaseModel):
    id: UUID
    camera: str
    occurred_at: datetime
    frame_asset: Optional[MediaAssetSchema]
    crop_asset: Optional[MediaAssetSchema]
    score: Optional[int]
    label: str
    created_at: datetime

    class Config:
        orm_mode = True


class NotificationSchema(BaseModel):
    id: UUID
    event_type: EventType
    event_id: Optional[UUID]
    status: NotificationStatus
    payload: Optional[dict]
    created_at: datetime
    sent_at: Optional[datetime]
    error: Optional[str]

    class Config:
        orm_mode = True


class JobRecordSchema(BaseModel):
    id: UUID
    job_type: str
    status: JobStatus
    payload: Optional[dict]
    created_at: datetime
    updated_at: datetime
    error: Optional[str]

    class Config:
        orm_mode = True


class SettingSchema(BaseModel):
    key: str
    value: dict
    updated_at: datetime

    class Config:
        orm_mode = True
