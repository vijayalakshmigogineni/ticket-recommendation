from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.run import RunCompareResponse, RunRequest, RunTraceResponse
from api.services import run_service

router = APIRouter(prefix="/api/run", tags=["run"])


@router.post("", response_model=RunTraceResponse)
def run(request: RunRequest, session: Session = Depends(get_db)) -> RunTraceResponse:
    return run_service.run_pipeline_traced(session, request)


@router.post("/compare", response_model=RunCompareResponse)
def run_compare(request: RunRequest, session: Session = Depends(get_db)) -> RunCompareResponse:
    """Experimental: runs the production pipeline (with cross-encoder) and
    the no-reranker variant against the same email, for the dashboard's
    side-by-side comparison view. Does not affect POST /api/run."""
    return run_service.run_pipeline_compare(session, request)
