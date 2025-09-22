from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple
from uuid import UUID


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
    bbox: Tuple[int, int, int, int]
    score: float
    crop_bytes: bytes


@dataclass(frozen=True)
class PersonDetections:
    frame_id: UUID
    camera: str
    captured_at: datetime
    frame_bytes: bytes
    persons: list[Detection]


@dataclass(frozen=True)
class VehicleDetections:
    frame_id: UUID
    camera: str
    captured_at: datetime
    frame_bytes: bytes
    vehicles: list[Detection]
