import logging
from multiprocessing import Event, Queue, set_start_method

from ..config.settings import ProcessorSettings

logger = logging.getLogger("processor.supervisor")


class Supervisor:
    def __init__(self, settings: ProcessorSettings) -> None:
        self.settings = settings
        self.stop_event = Event()
        self.processes: dict = {}
        self.frame_queue = Queue(maxsize=settings.queue_size)
        self.person_queue = Queue(maxsize=settings.queue_size)
        self.vehicle_queue = Queue(maxsize=settings.queue_size)