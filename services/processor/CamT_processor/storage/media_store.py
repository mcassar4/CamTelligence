from pathlib import Path
from typing import Optional
from uuid import UUID

from oi_core.models import MediaType


class FileSystemMediaStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_frame(self, frame_id: UUID, image_bytes: bytes, tag: str = "") -> str:
        return self._write(MediaType.frame, frame_id, image_bytes, tag=tag)

    def save_person_crop(self, frame_id: UUID, image_bytes: bytes) -> str:
        return self._write(MediaType.person_crop, frame_id, image_bytes, unique=True)

    def save_vehicle_crop(self, frame_id: UUID, image_bytes: bytes) -> str:
        return self._write(MediaType.vehicle_crop, frame_id, image_bytes, unique=True)

    def _write(self, media_type: MediaType, frame_id: UUID, data: bytes, tag: str = "", unique: bool = False) -> str:
        folder = self.root / media_type.value
        folder.mkdir(parents=True, exist_ok=True)
        suffix = ""
        if unique:
            from uuid import uuid4

            suffix = f"_{uuid4()}"
        name = f"{frame_id}{tag}{suffix}.jpg"
        path = folder / name
        path.write_bytes(data)
        return str(path)

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def load(self, path: str) -> Optional[bytes]:
        target = Path(path)
        if not target.exists():
            return None
        return target.read_bytes()
