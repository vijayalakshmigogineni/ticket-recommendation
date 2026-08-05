"""Pydantic output schemas for the 5 generation templates + 2 QA judges.

Mirrors docs/generation_prompts.md and docs/generation_qa_checklist.md exactly.
Passed to client.messages.parse(..., output_format=<Model>) so the API enforces
the shape structurally -- these are the source of truth for generation output
shape, not just documentation of it.

Batch-mode templates (1, 2, 3, and batched 4) wrap their array in a single named
field rather than a bare top-level list: structured outputs / client.messages.parse()
require an object schema (a Pydantic BaseModel), not a bare JSON array, even though
generation_prompts.md's illustrative examples show a bare array -- the prompts/*.py
wire text reflects the object-wrapper shape actually sent to the API.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.enums import (
    DifficultyTier,
    LengthBucket,
    MessageIntent,
    NoiseLevel,
    SenderType,
    Tone,
    TicketCategory,
    TicketStatus,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Template 1: Customer Generation -----------------------------------------


class CustomerProductionFields(StrictModel):
    name: str
    inbox_email: str


class CustomerContact(StrictModel):
    name: str
    role: str
    email: str


class CustomerGenerationMetadata(StrictModel):
    specialty: str
    practice_size: str  # "solo" | "small_group" | "multi_location"
    primary_payers: list[str]
    pm_ehr_system: str
    contacts: list[CustomerContact]


class CustomerItem(StrictModel):
    temp_id: str
    production_fields: CustomerProductionFields
    generation_metadata: CustomerGenerationMetadata


class CustomerBatchOutput(StrictModel):
    customers: list[CustomerItem]


# --- Template 2: Ticket Generation (seed) ------------------------------------


class TicketProductionFields(StrictModel):
    subject: str
    category: TicketCategory
    status: TicketStatus
    created_at_offset_days: int
    closed_at_offset_days: int | None = None


class TicketGenerationMetadata(StrictModel):
    core_issue_summary: str
    distinguishing_details: str
    claim_number: str | None = None
    patient_id: str | None = None
    payer: str
    date_of_service: str | None = None
    procedure_description: str


class TicketSeedItem(StrictModel):
    temp_id: str
    production_fields: TicketProductionFields
    generation_metadata: TicketGenerationMetadata


class TicketSeedBatchOutput(StrictModel):
    tickets: list[TicketSeedItem]


# --- Template 3: Conversation Generation -------------------------------------


class MessageProductionFields(StrictModel):
    sender_type: SenderType
    sender_email: str
    day_offset: int
    body_text: str


class MessageGenerationMetadata(StrictModel):
    intent_type: MessageIntent
    tone: Tone
    length_bucket: LengthBucket
    noise_level: NoiseLevel


class MessageItem(StrictModel):
    production_fields: MessageProductionFields
    generation_metadata: MessageGenerationMetadata


class TicketConversation(StrictModel):
    ticket_temp_id: str
    messages: list[MessageItem]


class ConversationBatchOutput(StrictModel):
    conversations: list[TicketConversation]


# --- Template 4: Eval Query Generation ---------------------------------------


class EvalQueryOutput(StrictModel):
    email_text: str


class EvalQueryScenarioItem(StrictModel):
    scenario_temp_id: str
    email_text: str


class EvalQueryBatchOutput(StrictModel):
    eval_queries: list[EvalQueryScenarioItem]


# --- Template 5: Ground-Truth Label Generation (blind judge) -----------------


class LabelOutput(StrictModel):
    matched_label: str | None = None
    should_match: bool
    difficulty_tier: DifficultyTier
    distractor_labels: list[str]
    reasoning: str


# --- Judge 1: Ticket & Conversation Consistency ------------------------------


class IntentMismatch(StrictModel):
    message_index: int
    labeled_intent: str
    issue: str


class Judge1Output(StrictModel):
    category_consistent: bool
    suggested_category: TicketCategory | None = None
    sibling_pairing_plausible: bool | None = None
    flow_issues: list[str]
    intent_mismatches: list[IntentMismatch]
    verdict: str  # "pass" | "flag" | "fail"
    reasoning: str


# --- Judge 2: Distractor Realism ---------------------------------------------


class Judge2Output(StrictModel):
    is_realistic_distractor: bool
    shared_surface_features: list[str]
    reasoning: str
