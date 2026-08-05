from __future__ import annotations

from fastapi import APIRouter

from api.schemas.evaluation import ABBenchmarkResponse, EvaluationStatusResponse
from api.services import evaluation_service

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/status", response_model=EvaluationStatusResponse)
def get_evaluation_status() -> EvaluationStatusResponse:
    return evaluation_service.get_evaluation_status()


@router.get("/ab-benchmark", response_model=ABBenchmarkResponse)
def get_ab_benchmark_status() -> ABBenchmarkResponse:
    return evaluation_service.get_ab_benchmark_status()
