import logging
import os
import time
from multiprocessing import Event, Process, Queue

from ..detector.movement_detector import MovementDetector
from ..detector.yolo_detector import CocoYoloDetector
from ..dto import PersonDetections, PoisonPill, VehicleDetections
from ..image_ops import decode_image
from ..logging_utils import configure_logging

logger = logging.getLogger("processor.detection")


class DetectionWorker(Process):
    def __init__(
        self,
        frame_queue: Queue,
        person_queue: Queue,
        vehicle_queue: Queue,
        stop_event: Event,
        motion_history: int,
        motion_kernel_size: int,
        motion_min_area: int,
        motion_debug_dir: str,
        motion_max_foreground_ratio: float,
    ):
        super().__init__(daemon=True)
        self.frame_queue = frame_queue
        self.person_queue = person_queue
        self.vehicle_queue = vehicle_queue
        self.stop_event = stop_event
        self.yolo = CocoYoloDetector()
        self.motion_history = motion_history
        self.motion_kernel_size = motion_kernel_size
        self.motion_min_area = motion_min_area
        self.motion_debug_dir = motion_debug_dir
        self.motion_max_foreground_ratio = motion_max_foreground_ratio
        self.cam_buffers: dict[str, MovementDetector] = {}
        self.cam_buffers_init: dict[str, bool] = {}
        self._last_queue_warn = 0.0
        self._queue_warn_interval = 5.0  # seconds
        self.motion_overlap_threshold = 0.2  # motion must cover at least 20% of a YOLO box


    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        logger.info("Detection worker started")
        while not self.stop_event.is_set():
            job = self.frame_queue.get()
            if isinstance(job, PoisonPill):
                self._fanout_poison()
                break
            self._maybe_warn_queue_backpressure(job.camera)
            motion_boxes = []
            try:
                image = decode_image(job.image_bytes)

                # Run motion detection first
                if job.camera in self.cam_buffers:
                    
                    motion_detector = self.cam_buffers[job.camera]
                    motion_boxes = motion_detector.detect(image)
                    
                    # If no motion detected, skip this frame
                    if not motion_boxes:
                        logger.debug(
                            "Skipped frame due to no motion",
                            extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id)}},
                        )
                        continue
                else: # First frame, initialize only and run motion detection next time
                    debug_dir = self.motion_debug_dir if logger.isEnabledFor(logging.DEBUG) else None
                    motion_detector = MovementDetector(
                        history=self.motion_history,
                        kernel_size=self.motion_kernel_size,
                        min_area=self.motion_min_area,
                        debug_dir=debug_dir,
                        camera=job.camera,
                        max_foreground_ratio=self.motion_max_foreground_ratio,
                    )
                    self.cam_buffers[job.camera] = motion_detector
                    
                # Now run YOLO detection
                predictions = self.yolo.predict(image)
            
            except Exception:
                logger.exception(
                    "Detection failed",
                    extra={"extra_payload": {"camera": job.camera, "frame_id": str(job.frame_id)}},
                )
                predictions = None
                image = None
                continue

            persons_raw = predictions.get("persons") if predictions else []
            vehicles_raw = predictions.get("vehicles") if predictions else []

            persons = self._filter_by_motion_overlap(persons_raw, motion_boxes)
            vehicles = self._filter_by_motion_overlap(vehicles_raw, motion_boxes)

            if persons:
                self._safe_put(
                    self.person_queue,
                    PersonDetections(
                        frame_id=job.frame_id,
                        camera=job.camera,
                        captured_at=job.captured_at,
                        frame_bytes=job.image_bytes,
                        persons=persons,
                    ),
                )
                logger.debug(
                    "Enqueued person detections",
                    extra={
                        "extra_payload": {
                            "camera": job.camera,
                            "frame_id": str(job.frame_id),
                            "count": len(persons),
                        }
                    },
                )
            if vehicles:
                self._safe_put(
                    self.vehicle_queue,
                    VehicleDetections(
                        frame_id=job.frame_id,
                        camera=job.camera,
                        captured_at=job.captured_at,
                        frame_bytes=job.image_bytes,
                        vehicles=vehicles,
                    ),
                )
                logger.debug(
                    "Enqueued vehicle detections",
                    extra={
                        "extra_payload": {
                            "camera": job.camera,
                            "frame_id": str(job.frame_id),
                            "count": len(vehicles),
                        }
                    },
                )
        self._fanout_poison()

    def _fanout_poison(self) -> None:
        try:
            self.person_queue.put_nowait(PoisonPill())
            self.vehicle_queue.put_nowait(PoisonPill())
        except Exception:
            pass

    def _safe_put(self, queue: Queue, item) -> None:
        while not self.stop_event.is_set():
            try:
                queue.put(item, timeout=0.5)
                return
            except Exception:
                continue

    def _filter_by_motion_overlap(self, detections, motion_boxes: list[tuple[int, int, int, int]]):
        """Keep YOLO detections only if motion overlaps >= threshold of their area."""
        if not detections or not motion_boxes:
            return []
        filtered = []
        for det in detections:
            if self._has_motion_overlap(det.bbox, motion_boxes):
                filtered.append(det)
        if detections and filtered != detections:
            logger.debug(
                "Filtered detections by motion overlap",
                extra={
                    "extra_payload": {
                        "kept": len(filtered),
                        "dropped": len(detections) - len(filtered),
                        "threshold": self.motion_overlap_threshold,
                    }
                },
            )
        return filtered

    def _has_motion_overlap(self, bbox: tuple[int, int, int, int], motion_boxes: list[tuple[int, int, int, int]]) -> bool:
        x1, y1, w, h = bbox
        if w <= 0 or h <= 0:
            return False
        x2 = x1 + w
        y2 = y1 + h
        det_area = float(w * h)
        threshold_area = det_area * self.motion_overlap_threshold

        for mx, my, mw, mh in motion_boxes:
            if mw <= 0 or mh <= 0:
                continue
            mx2 = mx + mw
            my2 = my + mh

            inter_w = min(x2, mx2) - max(x1, mx)
            inter_h = min(y2, my2) - max(y1, my)
            if inter_w <= 0 or inter_h <= 0:
                continue

            inter_area = inter_w * inter_h
            if inter_area >= threshold_area:
                return True
        return False

    def _maybe_warn_queue_backpressure(self, camera: str) -> None:
        """Warn if the frame queue is filling faster than we process."""
        now = time.monotonic()
        if now - self._last_queue_warn < self._queue_warn_interval:
            return
        try:
            qsize = self.frame_queue.qsize()
        except Exception:
            return
        maxsize = getattr(self.frame_queue, "_maxsize", 0) or 0
        if maxsize > 0:
            threshold = max(1, int(maxsize * 0.7))
        else:
            threshold = 10  # fallback heuristic
        if qsize >= threshold:
            self._last_queue_warn = now
            logger.warning(
                "Detection backlog is growing; consider reducing ingestion rate or increasing worker capacity",
                extra={"extra_payload": {"frame_queue_size": qsize, "frame_queue_maxsize": maxsize, "camera": camera}},
            )
