from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas.tickets import CreateCustomerRequest, CustomerListItem, CustomerListResponse
from api.services import customers_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=CustomerListResponse)
def list_customers(session: Session = Depends(get_db)) -> CustomerListResponse:
    return customers_service.list_customers(session)


@router.post("", response_model=CustomerListItem, status_code=201)
def create_customer(
    request: CreateCustomerRequest, session: Session = Depends(get_db)
) -> CustomerListItem:
    return customers_service.create_customer(session, request)
