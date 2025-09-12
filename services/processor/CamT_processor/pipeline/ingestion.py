import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

import cv2

from ..dto import FrameJob, PoisonPill
from ..logging_utils import configure_logging

logger = logging.getLogger("processor.ingestion")


@dataclass
class CameraConfig:
    name: str
    source: str
    poll_interval: float


def parse_camera_sources(raw_sources: List[str], default_poll: float) -> List[CameraConfig]:
    configs: List[CameraConfig] = []
    for raw in raw_sources:
        if "=" in raw:
            name, source = raw.split("=", 1)
        else:
            name, source = raw, raw
        configs.append(CameraConfig(name=name.strip(), source=source.strip(), poll_interval=default_poll))
    return configs


class IngestionWorker(Process):
    def __init__(self, queue: Queue, cameras: List[CameraConfig], stop_event: Event):
        super().__init__(daemon=True)
        self.queue = queue
        self.cameras = cameras
        self.stop_event = stop_event
        self._file_cursors: Dict[str, float] = {}

    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        logger.info("Ingestion starting", extra={"extra_payload": {"cameras": [c.name for c in self.cameras]}})
        while not self.stop_event.is_set():
            for camera in self.cameras:
                try:
                    if camera.source.startswith("rtsp") or camera.source.startswith("http"):
                        self._read_stream(camera)
                    else:
                        self._poll_files(camera)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Ingestion error", extra={"extra_payload": {"camera": camera.name, "error": str(exc)}})
                time.sleep(camera.poll_interval)
        try:
            self.queue.put_nowait(PoisonPill())
        except Exception:
            pass

    def _poll_files(self, camera: CameraConfig) -> None:
        path = Path(camera.source)
        if path.is_dir():
            images = sorted(path.glob("*.jpg")) + sorted(path.glob("*.png"))
        else:
            images = [path] if path.exists() else []
        last_ts = self._file_cursors.get(camera.name, 0.0)
        new_count = 0
        for img_path in images:
            stat = img_path.stat()
            if stat.st_mtime <= last_ts:
                continue
            data = img_path.read_bytes()
            job = FrameJob(
                frame_id=uuid4(),
                camera=camera.name,
                captured_at=datetime.utcnow(),
                image_bytes=data
            )
            self._enqueue(job)
            new_count += 1
            last_ts = stat.st_mtime
        self._file_cursors[camera.name] = last_ts
        if new_count:
            logger.debug(
                "Ingested files",
                extra={"extra_payload": {"camera": camera.name, "count": new_count, "source": str(path)}},
            )

    def _read_stream(self, camera: CameraConfig) -> None:
        cap = cv2.VideoCapture(camera.source)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            logger.warning(
                "Failed to read frame from stream",
                extra={"extra_payload": {"camera": camera.name, "source": camera.source}},
            )
            return
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            logger.warning(
                "Failed to encode frame",
                extra={"extra_payload": {"camera": camera.name, "source": camera.source}},
            )
            return
        self._enqueue(FrameJob(
            frame_id=uuid4(),
            camera=camera.name,
            captured_at=datetime.utcnow(),
            image_bytes=buffer.tobytes()
        ))
        logger.debug(
            "Enqueued stream frame",
            extra={"extra_payload": {"camera": camera.name, "source": camera.source}},
        )

    def _enqueue(self, job: FrameJob) -> None:
        while not self.stop_event.is_set():
            try:
                self.queue.put(job, timeout=0.5)
                logger.debug(
                    "Frame enqueued",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id)}},
                )
                return
            except Exception:
                time.sleep(0.1)


def main() -> None:
    import argparse
    import signal
    from multiprocessing import freeze_support, set_start_method
    from queue import Empty

    parser = argparse.ArgumentParser(description="Run the ingestion worker standalone.")
    parser.add_argument(
        "--camera",
        action="append",
        default=None,
        help=(
            "Camera source in the form 'name=source' (repeatable). "
            "If omitted, uses env CAMERA_SOURCES (comma-separated)."
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("FRAME_POLL_INTERVAL", "1.0")),
        help="Seconds between polls (default: env FRAME_POLL_INTERVAL or 1.0).",
    )
    parser.add_argument(
        "--queue-size",
        type=int,
        default=int(os.getenv("QUEUE_SIZE", "512")),
        help="Multiprocessing queue max size (default: env QUEUE_SIZE or 512).",
    )
    args = parser.parse_args()

    sources = args.camera
    if not sources:
        raw = os.getenv("CAMERA_SOURCES", "")
        sources = [item.strip() for item in raw.split(",") if item.strip()]

    if not sources:
        raise SystemExit(
            "No camera sources provided. Pass --camera name=source (repeatable) or set CAMERA_SOURCES."
        )

    freeze_support()
    try:
        set_start_method("spawn")
    except RuntimeError:
        pass

    configure_logging(os.getenv("LOG_LEVEL"))

    stop_event = Event()
    queue: Queue = Queue(maxsize=args.queue_size)
    cameras = parse_camera_sources(sources, default_poll=args.poll_interval)
    worker = IngestionWorker(queue=queue, cameras=cameras, stop_event=stop_event)

    def _handle_shutdown(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_shutdown)

    worker.start()
    logger.info(
        "Standalone ingestion started",
        extra={"extra_payload": {"cameras": [c.name for c in cameras], "queue_size": args.queue_size}},
    )
    try:
        while not stop_event.is_set():
            try:
                item = queue.get(timeout=0.5)
            except Empty:
                continue
            if isinstance(item, PoisonPill):
                logger.info("Received shutdown signal", extra={"extra_payload": {"reason": item.reason}})
                break
            if isinstance(item, FrameJob):
                logger.info(
                    "Received frame",
                    extra={
                        "extra_payload": {
                            "camera": item.camera,
                            "frame_id": str(item.frame_id),
                            "bytes": len(item.image_bytes),
                        }
                    },
                )
    finally:
        stop_event.set()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
