import logging
import os
from uuid import UUID
from datetime import datetime
from multiprocessing import Event, Process, Queue
from typing import Optional

from sqlalchemy.exc import IntegrityError
from psycopg2 import DatabaseError

from ct_core import engine, get_session
from ct_core.models import EventType, JobRecord, JobStatus, MediaAsset, MediaType, Notification, NotificationStatus, PersonEvent, VehicleEvent

from sqlalchemy import select

from ..dto import NotificationJob, PersonDetections, PoisonPill, VehicleDetections
from ..storage.media_store import FileSystemMediaStore
from ..logging_utils import configure_logging

logger = logging.getLogger("processor.events")


def get_or_create_frame_asset(
    session,
    media_store: FileSystemMediaStore,
    frame_id: UUID,
    frame_bytes: bytes,
    camera: str,
    tag: str = "",
) -> MediaAsset:
    frame_path = media_store.save_frame(frame_id, frame_bytes, tag=tag)
    try:
        existing = session.scalars(select(MediaAsset).where(MediaAsset.path == frame_path)).first()
        if existing:
            return existing
        frame_asset = MediaAsset(media_type=MediaType.frame, path=frame_path, attributes={"camera": camera})
        session.add(frame_asset)
        session.flush()
        return frame_asset
    except IntegrityError:
        session.rollback()
        recovered = session.scalars(select(MediaAsset).where(MediaAsset.path == frame_path)).first()
        if recovered:
            return recovered
        raise
    except DatabaseError as exc:
        session.rollback()
        logger.exception(
            "Database error when getting/creating frame asset",
            extra={"extra_payload": {"camera": camera, "frame_id": str(frame_id), "error": str(exc), "path": frame_path}},
        )
        raise


class PersonEventWriter(Process):
    def __init__(self, queue: Queue, notification_queue: Queue, stop_event: Event, media_root: str):
        super().__init__(daemon=True)
        self.queue = queue
        self.notification_queue = notification_queue
        self.stop_event = stop_event
        self.media_root = media_root
        self.media_store = FileSystemMediaStore(media_root)

    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        try:
            engine.dispose()
        except Exception:
            pass
        while not self.stop_event.is_set():
            job = self.queue.get()
            if isinstance(job, PoisonPill):
                self._send_poison()
                break
            self._handle_job(job)
        self._send_poison()

    def _handle_job(self, job: PersonDetections) -> None:
        if not job.persons:
            return
        logger.debug(
            "Processing person detections",
            extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "count": len(job.persons)}},
        )
        with get_session() as session:
            try:
                notification_jobs = []
                with session.begin():
                    frame_asset = get_or_create_frame_asset(
                        session, self.media_store, job.frame_id, job.frame_bytes, job.camera, tag="_person"
                    )
                    for detection in job.persons:
                        crop_path = self.media_store.save_person_crop(job.frame_id, detection.crop_bytes)
                        crop_asset = MediaAsset(media_type=MediaType.person_crop, path=crop_path, attributes={"camera": job.camera})
                        session.add(crop_asset)
                        session.flush()

                        person_event = PersonEvent(
                            camera=job.camera,
                            occurred_at=job.captured_at,
                            frame_asset_id=frame_asset.id,
                            crop_asset_id=crop_asset.id,
                            score=int(detection.score) if detection.score else None,
                        )
                        session.add(person_event)
                        session.add(
                            JobRecord(
                                job_type="person_event",
                                status=JobStatus.finished,
                                payload={"frame_id": str(job.frame_id), "camera": job.camera},
                            )
                        )
                        notification_jobs.append(
                            NotificationJob(
                                event_type="person",
                                camera=job.camera,
                                occurred_at=job.captured_at,
                                crop_path=crop_path,
                                event_id=person_event.id,
                            )
                        )
                for note in notification_jobs:
                    self._enqueue_notification(note)
            except IntegrityError as exc:
                session.rollback()
                logger.warning(
                    "Duplicate media asset detected, skipping person event",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "error": str(exc)}})
            except Exception as exc:
                session.rollback()
                logger.exception(
                    "Unexpected error in person writer",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "error": str(exc)}})

    def _enqueue_notification(self, job: NotificationJob) -> None:
        try:
            self.notification_queue.put_nowait(job)
        except Exception:
            logger.warning("Notification queue full, dropping", extra={"extra_payload": {"camera": job.camera}})

    def _send_poison(self) -> None:
        try:
            self.notification_queue.put_nowait(PoisonPill())
        except Exception:
            pass


class VehicleEventWriter(Process):
    def __init__(self, queue: Queue, notification_queue: Queue, stop_event: Event, media_root: str):
        super().__init__(daemon=True)
        self.queue = queue
        self.notification_queue = notification_queue
        self.stop_event = stop_event
        self.media_root = media_root
        self.media_store = FileSystemMediaStore(media_root)

    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        try:
            engine.dispose()
        except Exception:
            pass
        while not self.stop_event.is_set():
            job = self.queue.get()
            if isinstance(job, PoisonPill):
                self._send_poison()
                break
            self._handle_job(job)
        self._send_poison()

    def _handle_job(self, job: VehicleDetections) -> None:
        if not job.vehicles:
            return
        logger.debug(
            "Processing vehicle detections",
            extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "count": len(job.vehicles)}},
        )
        with get_session() as session:
            try:
                notification_jobs = []
                with session.begin():
                    frame_asset = get_or_create_frame_asset(
                        session, self.media_store, job.frame_id, job.frame_bytes, job.camera, tag="_vehicle"
                    )
                    for detection in job.vehicles:
                        crop_path = self.media_store.save_vehicle_crop(job.frame_id, detection.crop_bytes)
                        crop_asset = MediaAsset(media_type=MediaType.vehicle_crop, path=crop_path, attributes={"camera": job.camera})
                        session.add(crop_asset)
                        session.flush()

                        vehicle_event = VehicleEvent(
                            camera=job.camera,
                            occurred_at=job.captured_at,
                            frame_asset_id=frame_asset.id,
                            crop_asset_id=crop_asset.id,
                            score=int(detection.score) if detection.score else None,
                        )
                        session.add(vehicle_event)
                        session.add(
                            JobRecord(
                                job_type="vehicle_event",
                                status=JobStatus.finished,
                                payload={"frame_id": str(job.frame_id), "camera": job.camera},
                            )
                        )
                        notification_jobs.append(
                            NotificationJob(
                                event_type="vehicle",
                                camera=job.camera,
                                occurred_at=job.captured_at,
                                crop_path=crop_path,
                                event_id=vehicle_event.id,
                            )
                        )
                for note in notification_jobs:
                    self._enqueue_notification(note)
            except IntegrityError as exc:
                session.rollback()
                logger.warning(
                    "Duplicate media asset detected, skipping vehicle event",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "error": str(exc)}},
                )
            except Exception as exc:
                session.rollback()
                logger.exception(
                    "Unexpected error in vehicle writer",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id), "error": str(exc)}},
                )

    def _enqueue_notification(self, job: NotificationJob) -> None:
        try:
            self.notification_queue.put_nowait(job)
        except Exception:
            logger.warning("Notification queue full, dropping", extra={"extra_payload": {"camera": job.camera}})

    def _send_poison(self) -> None:
        try:
            self.notification_queue.put_nowait(PoisonPill())
        except Exception:
            pass
