import mimetypes
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from oi_core.models import MediaAsset

from ..core.config import get_settings
from ..dependencies import db_dep

router = APIRouter(prefix="/media", tags=["media"])


def _resolve_media_path(asset_path: str, media_root: Path) -> Path:
    candidate = Path(asset_path)
    if not candidate.is_absolute():
        candidate = media_root / candidate
    resolved = candidate.resolve()
    if not str(resolved).startswith(str(media_root)):
        raise HTTPException(status_code=400, detail="Media path is outside configured root")
    return resolved


@router.get("/{asset_id}")
def get_media_asset(asset_id: UUID, db: Session = Depends(db_dep)):
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    settings = get_settings()
    media_root = Path(settings.media_root).resolve()
    path = _resolve_media_path(asset.path, media_root)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing")

    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type or "application/octet-stream")
