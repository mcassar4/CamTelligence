from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID, uuid4


BoundingBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class PoisonPill:
    reason: str = "shutdown"


@dataclass(frozen=True)
class FrameJob:
    frame_id: UUID
    camera: str
    captured_at: datetime
    image_bytes: bytes


@dataclass(frozen=True)
class Detection:
    bbox: BoundingBox
    score: float
    crop_bytes: bytes


@dataclass(frozen=True)
class PersonDetections:
    frame_id: UUID
    camera: str
    captured_at: datetime
    frame_bytes: bytes
    persons: List[Detection] = field(default_factory=list)


@dataclass(frozen=True)
class VehicleDetections:
    frame_id: UUID
    camera: str
    captured_at: datetime
    frame_bytes: bytes
    vehicles: List[Detection] = field(default_factory=list)


@dataclass(frozen=True)
class NotificationJob:
    event_type: str
    camera: str
    occurred_at: datetime
    crop_path: Optional[str]
    event_id: Optional[UUID] = None

