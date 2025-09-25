import logging
import os
from multiprocessing import Event, Queue, set_start_method

from ..config.settings import ProcessorSettings
from ..logging_utils import configure_logging
from .ingestion import IngestionWorker, parse_camera_sources
from .detection import DetectionWorker

logger = logging.getLogger("processor.supervisor")


class Supervisor:
    def __init__(self, settings: ProcessorSettings) -> None:
        self.settings = settings
        self.stop_event = Event()
        self.processes: dict = {}
        self.frame_queue = Queue(maxsize=settings.queue_size)
        self.person_queue = Queue(maxsize=settings.queue_size)
        self.vehicle_queue = Queue(maxsize=settings.queue_size)

    def start(self) -> None:
        try:
            set_start_method("spawn")
        except RuntimeError:
            pass
        configure_logging(os.getenv("LOG_LEVEL"))
        cameras = parse_camera_sources(self.settings.camera_sources, self.settings.frame_poll_interval)
        if not cameras:
            logger.warning("No camera sources configured; processor will idle until sources are provided")
        
        factories = {
            "ingestion": lambda: IngestionWorker(self.frame_queue, cameras=cameras, stop_event=self.stop_event),
            "detection": lambda: DetectionWorker(
                self.frame_queue,
                self.person_queue,
                self.vehicle_queue,
                self.stop_event,
                motion_history=self.settings.motion_history,
                motion_kernel_size=self.settings.motion_kernel_size,
                motion_min_area=self.settings.motion_min_area,
                motion_debug_dir=self.settings.motion_debug_dir,
                motion_max_foreground_ratio=self.settings.motion_max_foreground_ratio,
            )
        }

        self.processes = {name: factory() for name, factory in factories.items()}
        for proc in self.processes.values():
            proc.start()
