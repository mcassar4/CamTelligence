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


    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        logger.info("Detection worker started")
        while not self.stop_event.is_set():
            job = self.frame_queue.get()
            
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

            persons = predictions.get("persons") if predictions else None
            vehicles = predictions.get("vehicles") if predictions else None

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