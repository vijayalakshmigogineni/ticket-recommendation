from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from api.errors import NotFoundError
from api.schemas.common import CustomerRef, TicketRef
from api.schemas.feedback import FeedbackListResponse, FeedbackRecord, RecordFeedbackRequest
from recommender.models import Customer, ManagerDecision, RecommendationFeedback, Ticket


def _customer_ref(customer: Customer) -> CustomerRef:
    return CustomerRef(id=customer.id, name=customer.name, inbox_email=customer.inbox_email)


def _ticket_ref(ticket: Ticket | None) -> TicketRef | None:
    if ticket is None:
        return None
    return TicketRef(
        id=ticket.id,
        subject=ticket.subject,
        category=ticket.category,
        status=ticket.status.value,
        customer_name=ticket.customer.name,
    )


def _to_record(feedback: RecommendationFeedback) -> FeedbackRecord:
    return FeedbackRecord(
        id=feedback.id,
        customer=_customer_ref(feedback.customer),
        sender_email=feedback.sender_email,
        subject=feedback.subject,
        body=feedback.body,
        should_attach=feedback.should_attach,
        recommended_ticket=_ticket_ref(feedback.recommended_ticket),
        confidence=feedback.confidence,
        explanation=feedback.explanation,
        manager_decision=feedback.manager_decision.value,
        corrected_ticket=_ticket_ref(feedback.corrected_ticket),
        notes=feedback.notes,
        created_at=feedback.created_at,
    )


def record_feedback(session: Session, request: RecordFeedbackRequest) -> FeedbackRecord:
    customer = session.get(Customer, request.customer_id)
    if customer is None:
        raise NotFoundError(f"customer {request.customer_id} not found")

    feedback = RecommendationFeedback(
        customer_id=request.customer_id,
        sender_email=request.sender_email,
        subject=request.subject,
        body=request.body,
        should_attach=request.should_attach,
        recommended_ticket_id=request.recommended_ticket_id,
        confidence=request.confidence,
        explanation=request.explanation,
        manager_decision=ManagerDecision(request.manager_decision),
        corrected_ticket_id=request.corrected_ticket_id,
        notes=request.notes,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return _to_record(feedback)


def list_feedback(
    session: Session,
    customer_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> FeedbackListResponse:
    query = session.query(RecommendationFeedback)
    if customer_id is not None:
        query = query.filter(RecommendationFeedback.customer_id == customer_id)

    total = query.count()
    rows = (
        query.order_by(RecommendationFeedback.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return FeedbackListResponse(items=[_to_record(r) for r in rows], total=total)
