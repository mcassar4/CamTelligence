import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from multiprocessing import Event, Process, Queue
from pathlib import Path
from typing import Dict, Optional

import httpx

from ..dto import NotificationJob, PoisonPill
from ..logging_utils import configure_logging

logger = logging.getLogger("processor.notifications")


@dataclass
class TelegramSettings:
    token: str
    chat_id: str
    debounce_seconds: int = 60


class TelegramNotifier:
    def __init__(self, settings: TelegramSettings) -> None:
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{settings.token}"

    def send(self, message: str, image_path: Optional[str] = None) -> None:
        with httpx.Client(timeout=10) as client:
            if image_path and Path(image_path).exists():
                files = {"photo": Path(image_path).read_bytes()}
                data = {"chat_id": self.settings.chat_id, "caption": message}
                resp = client.post(f"{self.base_url}/sendPhoto", data=data, files={"photo": ("event.jpg", files["photo"])})
            else:
                resp = client.post(f"{self.base_url}/sendMessage", json={"chat_id": self.settings.chat_id, "text": message})
            resp.raise_for_status()


class NotificationWorker(Process):
    def __init__(self, queue: Queue, stop_event: Event, settings: Optional[TelegramSettings]):
        super().__init__(daemon=True)
        self.queue = queue
        self.stop_event = stop_event
        self.settings = settings
        self.notifier = TelegramNotifier(settings) if settings else None
        self._last_sent: Dict[str, datetime] = {}

    def run(self) -> None:
        configure_logging(os.getenv("LOG_LEVEL"))
        while not self.stop_event.is_set():
            job = self.queue.get()
            if isinstance(job, PoisonPill):
                break
            if not self.notifier:
                continue
            if self._should_skip(job):
                continue
            try:
                self._deliver(job)
                self._last_sent[job.camera] = datetime.utcnow()
            except Exception as exc:  # pragma: no cover - best effort
                logger.error("Failed to send notification", extra={"extra_payload": {"error": str(exc)}})

    def _should_skip(self, job: NotificationJob) -> bool:
        last = self._last_sent.get(job.camera)
        if not last:
            return False
        return (datetime.utcnow() - last) < timedelta(seconds=self.settings.debounce_seconds)  # type: ignore[arg-type]

    def _deliver(self, job: NotificationJob) -> None:
        if job.event_type == "vehicle":
            title = "Vehicle detected"
        elif job.event_type == "person":
            title = "Person detected"
        else:
            title = "Event detected"
        message = f"{title}\nCamera: {job.camera}\nWhen: {job.occurred_at.isoformat()}"
        self.notifier.send(message, job.crop_path)
