from typing import Optional

from sqlalchemy.orm import Session

from oi_core.models import Setting


class SettingsRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, key: str) -> Optional[Setting]:
        return self.session.query(Setting).filter(Setting.key == key).first()

    def upsert(self, key: str, value: dict) -> Setting:
        setting = self.get(key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        self.session.commit()
        self.session.refresh(setting)
        return setting
