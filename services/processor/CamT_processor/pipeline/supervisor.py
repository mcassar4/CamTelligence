import logging
import os
from multiprocessing import Event, Queue, set_start_method

from ..config.settings import ProcessorSettings
from ..logging_utils import configure_logging
from .ingestion import IngestionWorker, parse_camera_sources


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
