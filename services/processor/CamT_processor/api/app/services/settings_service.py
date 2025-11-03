from sqlalchemy.orm import Session

from oi_core.models import Setting

from ..repositories.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, session: Session):
        self.repo = SettingsRepository(session)

    def upsert(self, key: str, value: dict) -> Setting:
        return self.repo.upsert(key, value)

    def get(self, key: str) -> Setting | None:
        return self.repo.get(key)
