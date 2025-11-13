import logging
import os
import signal
import time
from multiprocessing import Event, Queue, set_start_method
from typing import List

from ..config.settings import ProcessorSettings
from ..dto import PoisonPill
from ..logging_utils import configure_logging
from ..notifications.telegram import NotificationWorker, TelegramSettings
from .detection import DetectionWorker
from .event_writer import PersonEventWriter, VehicleEventWriter
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
        self.notification_queue = Queue(maxsize=settings.queue_size)

    def start(self) -> None:
        try:
            set_start_method("spawn")
        except RuntimeError:
            pass
        configure_logging(os.getenv("LOG_LEVEL"))
        cameras = parse_camera_sources(self.settings.camera_sources, self.settings.frame_poll_interval)
        telegram_settings = None
        if self.settings.notifications_enabled and self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            telegram_settings = TelegramSettings(
                token=self.settings.telegram_bot_token,
                chat_id=self.settings.telegram_chat_id,
                debounce_seconds=self.settings.notification_debounce_seconds,
            )

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
            ),
            "person_writer": lambda: PersonEventWriter(
                self.person_queue,
                self.notification_queue,
                self.stop_event,
                media_root=self.settings.media_root,
            ),
            "vehicle_writer": lambda: VehicleEventWriter(
                self.vehicle_queue,
                self.notification_queue,
                self.stop_event,
                media_root=self.settings.media_root,
            ),
            "notifier": lambda: NotificationWorker(self.notification_queue, self.stop_event, settings=telegram_settings),
        }

        self.processes = {name: factory() for name, factory in factories.items()}
        for proc in self.processes.values():
            proc.start()
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        self._monitor(factories)

    def _monitor(self, factories) -> None:
        while not self.stop_event.is_set():
            for name, proc in list(self.processes.items()):
                if not proc.is_alive():
                    logger.warning("Process died, restarting", extra={"extra_payload": {"process": name}})
                    replacement = factories[name]()
                    replacement.start()
                    self.processes[name] = replacement
            time.sleep(1)

    def _shutdown(self, *_args) -> None:
        self.stop_event.set()
        try:
            self.frame_queue.put_nowait(PoisonPill())
            self.person_queue.put_nowait(PoisonPill())
            self.vehicle_queue.put_nowait(PoisonPill())
            self.notification_queue.put_nowait(PoisonPill())
        except Exception:
            pass
        for proc in self.processes.values():
            if proc.is_alive():
                proc.join(timeout=2)
