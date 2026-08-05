from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.feedback import FeedbackListResponse, FeedbackRecord, RecordFeedbackRequest
from api.services import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRecord, status_code=201)
def record_feedback(
    request: RecordFeedbackRequest, session: Session = Depends(get_db)
) -> FeedbackRecord:
    return feedback_service.record_feedback(session, request)


@router.get("", response_model=FeedbackListResponse)
def list_feedback(
    customer_id: uuid.UUID | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    session: Session = Depends(get_db),
) -> FeedbackListResponse:
    return feedback_service.list_feedback(session, customer_id, limit, offset)
