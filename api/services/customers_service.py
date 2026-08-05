from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.errors import ConflictError
from api.schemas.tickets import CreateCustomerRequest, CustomerListItem, CustomerListResponse
from recommender.models import Customer, Ticket


def list_customers(session: Session) -> CustomerListResponse:
    rows = (
        session.query(Customer, func.count(Ticket.id))
        .outerjoin(Ticket, Ticket.customer_id == Customer.id)
        .group_by(Customer.id)
        .order_by(Customer.name.asc())
        .all()
    )
    items = [
        CustomerListItem(id=c.id, name=c.name, inbox_email=c.inbox_email, ticket_count=count)
        for c, count in rows
    ]
    return CustomerListResponse(items=items)


def create_customer(session: Session, request: CreateCustomerRequest) -> CustomerListItem:
    name = request.name.strip()
    # Lowercased to match recommender.customer_identification.identify_customer's
    # normalization of the incoming sender address -- otherwise a customer
    # created here with mixed case would never actually match in the Playground.
    inbox_email = request.inbox_email.strip().lower()

    if not name or not inbox_email:
        raise ConflictError("name and inbox_email are both required")

    existing = session.query(Customer).filter(Customer.inbox_email == inbox_email).one_or_none()
    if existing is not None:
        raise ConflictError(f"a customer with inbox_email {inbox_email!r} already exists")

    customer = Customer(name=name, inbox_email=inbox_email)
    session.add(customer)
    session.commit()
    session.refresh(customer)

    return CustomerListItem(id=customer.id, name=customer.name, inbox_email=customer.inbox_email, ticket_count=0)
