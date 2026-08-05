from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.system import IndexInfoResponse, SystemSettingsResponse, SystemStatusResponse
from api.services import system_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def get_status(session: Session = Depends(get_db)) -> SystemStatusResponse:
    return system_service.get_system_status(session)


@router.get("/settings", response_model=SystemSettingsResponse)
def get_settings() -> SystemSettingsResponse:
    return system_service.get_system_settings()


@router.get("/index-info", response_model=IndexInfoResponse)
def get_index_info(session: Session = Depends(get_db)) -> IndexInfoResponse:
    return system_service.get_index_info(session)
