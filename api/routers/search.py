from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.search import VectorSearchRequest, VectorSearchResponse
from api.services import search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/vector", response_model=VectorSearchResponse)
def vector_search(
    request: VectorSearchRequest, session: Session = Depends(get_db)
) -> VectorSearchResponse:
    return search_service.vector_search(session, request)
