import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from oi_core import get_session
from oi_core.models import MediaAsset, Notification, PersonEvent, VehicleEvent

from ..config.janitor_settings import JanitorSettings

logger = logging.getLogger("janitor.retention")


def _is_safe_path(path: Path, media_root: Path) -> bool:
    try:
        return str(path.resolve()).startswith(str(media_root.resolve()))
    except Exception:
        return False


def _unlink_paths(paths: Iterable[Path], media_root: Path) -> int:
    removed = 0
    for path in paths:
        if not _is_safe_path(path, media_root):
            logger.warning("Skipping delete outside media root", extra={"extra_payload": {"path": str(path)}})
            continue
        try:
            if path.exists():
                path.unlink()
                removed += 1
        except Exception as exc:
            logger.warning("Failed to delete media file", extra={"extra_payload": {"path": str(path), "error": str(exc)}})
    return removed


def _gather_asset_paths(session: Session, asset_ids: Sequence[UUID]) -> list[Path]:
    if not asset_ids:
        return []
    stmt = select(MediaAsset.path).where(MediaAsset.id.in_(asset_ids))
    return [Path(row[0]) for row in session.execute(stmt)]


def cleanup_retention(settings: JanitorSettings) -> dict[str, int]:
    """
    Remove media and related DB rows older than the retention window.
    Returns counts for logging: {"person_events": n, "vehicle_events": n, "media_files": n}
    """
    cutoff = datetime.utcnow() - settings.retention_window
    media_root = Path(settings.media_root)
    counts = {
        "person_events": 0,
        "vehicle_events": 0,
        "media_files": 0,
        "notifications": 0,
        "media_assets": 0,
    }
    file_paths: list[Path] = []

    with get_session() as session:
        try:
            person_counts = _cleanup_person_events(session, cutoff)
            vehicle_counts = _cleanup_vehicle_events(session, cutoff)
            file_paths.extend(person_counts.pop("_file_paths", []))
            file_paths.extend(vehicle_counts.pop("_file_paths", []))
            for key, value in person_counts.items():
                counts[key] = counts.get(key, 0) + value
            for key, value in vehicle_counts.items():
                counts[key] = counts.get(key, 0) + value
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            logger.exception("Retention cleanup failed due to integrity error", extra={"extra_payload": {"error": str(exc)}})
            return counts
        except Exception as exc:
            session.rollback()
            logger.exception("Retention cleanup failed", extra={"extra_payload": {"error": str(exc)}})
            return counts

    # Delete files after DB commit to avoid dangling FKs on failure.
    counts["media_files"] = _unlink_paths(file_paths, media_root)
    return counts


def _cleanup_vehicle_events(session: Session, cutoff: datetime) -> dict[str, int]:
    result = {"vehicle_events": 0, "notifications": 0, "media_assets": 0, "_file_paths": []}
    stmt = select(
        VehicleEvent.id,
        VehicleEvent.frame_asset_id,
        VehicleEvent.crop_asset_id,
    ).where(VehicleEvent.occurred_at < cutoff)
    rows = session.execute(stmt).all()
    if not rows:
        return result

    event_ids = [row[0] for row in rows]
    asset_ids: list[UUID] = []
    for row in rows:
        if row[1]:
            asset_ids.append(row[1])
        if row[2]:
            asset_ids.append(row[2])

    session.execute(delete(Notification).where(Notification.event_id.in_(event_ids)))
    result["notifications"] = len(event_ids)
    session.execute(delete(VehicleEvent).where(VehicleEvent.id.in_(event_ids)))
    result["vehicle_events"] = len(event_ids)

    paths = _gather_asset_paths(session, asset_ids)
    session.execute(delete(MediaAsset).where(MediaAsset.id.in_(asset_ids)))
    result["media_assets"] = len(asset_ids)
    result["_file_paths"] = paths
    return result


def _cleanup_person_events(session: Session, cutoff: datetime) -> dict[str, int]:
    result = {"person_events": 0, "notifications": 0, "media_assets": 0, "_file_paths": []}
    stmt = select(
        PersonEvent.id,
        PersonEvent.frame_asset_id,
        PersonEvent.crop_asset_id,
    ).where(PersonEvent.occurred_at < cutoff)
    rows = session.execute(stmt).all()
    if not rows:
        return result

    event_ids = [row[0] for row in rows]
    asset_ids: list[UUID] = []
    for row in rows:
        if row[1]:
            asset_ids.append(row[1])
        if row[2]:
            asset_ids.append(row[2])

    session.execute(delete(Notification).where(Notification.event_id.in_(event_ids)))
    result["notifications"] = len(event_ids)
    session.execute(delete(PersonEvent).where(PersonEvent.id.in_(event_ids)))
    result["person_events"] = len(event_ids)

    paths = _gather_asset_paths(session, asset_ids)
    session.execute(delete(MediaAsset).where(MediaAsset.id.in_(asset_ids)))
    result["media_assets"] = len(asset_ids)
    result["_file_paths"] = paths
    return result
