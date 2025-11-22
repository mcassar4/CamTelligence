from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ct_core.schemas import SettingSchema

from ..dependencies import db_dep
from ..schemas import SettingsUpdate
from ..services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.put("/", response_model=SettingSchema)
def upsert_setting(payload: SettingsUpdate, db: Session = Depends(db_dep)):
    service = SettingsService(db)
    return service.upsert(payload.key, payload.value)
