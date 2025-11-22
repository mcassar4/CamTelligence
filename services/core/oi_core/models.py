import enum
import uuid

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import CHAR, TypeDecorator

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except Exception:
            return uuid.uuid4()


class MediaType(str, enum.Enum):
    frame = "frame"
    person_crop = "person_crop"
    vehicle_crop = "vehicle_crop"
    other = "other"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class EventType(str, enum.Enum):
    person = "person"
    vehicle = "vehicle"


class JobStatus(str, enum.Enum):
    queued = "queued"
    started = "started"
    finished = "finished"
    failed = "failed"
    dropped = "dropped"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    media_type = Column(Enum(MediaType), nullable=False)
    path = Column(String(1024), nullable=False, unique=True)
    attributes = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonEvent(Base):
    __tablename__ = "person_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    camera = Column(String(255), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    frame_asset_id = Column(GUID(), ForeignKey("media_assets.id"), nullable=True)
    crop_asset_id = Column(GUID(), ForeignKey("media_assets.id"), nullable=True)
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    frame_asset = relationship("MediaAsset", foreign_keys=[frame_asset_id])
    crop_asset = relationship("MediaAsset", foreign_keys=[crop_asset_id])


class VehicleEvent(Base):
    __tablename__ = "vehicle_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    camera = Column(String(255), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    frame_asset_id = Column(GUID(), ForeignKey("media_assets.id"), nullable=True)
    crop_asset_id = Column(GUID(), ForeignKey("media_assets.id"), nullable=True)
    score = Column(Integer, nullable=True)
    label = Column(String(128), nullable=False, default="vehicle")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    frame_asset = relationship("MediaAsset", foreign_keys=[frame_asset_id])
    crop_asset = relationship("MediaAsset", foreign_keys=[crop_asset_id])


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_type = Column(Enum(EventType), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.pending)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)


class JobRecord(Base):
    __tablename__ = "jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(64), nullable=False)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.queued)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    error = Column(Text, nullable=True)
