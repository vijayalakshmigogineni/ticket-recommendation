import enum


class TicketCategory(str, enum.Enum):
    """Which operational team owns this ticket (broad).

    Values are our own readable vocabulary, not the production system's
    exact strings -- see PRODUCTION_CATEGORY_LABEL below for the translation
    layer, used only at an eventual integration boundary, never scattered
    through generation code. No IssueType sub-classification: confirmed the
    real production ticketing system has no such concept, category is the
    only classification axis on a ticket.

    No PATIENT_CALLING value: confirmed with the user this category is
    slated for removal from production too (not just irrelevant to an
    email-driven benchmark) -- not modeled here at all.
    """

    CLAIMS = "claims"
    PAYMENT_POSTING = "payment_posting"
    PRIOR_AUTHORIZATION = "prior_authorization"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ELIGIBILITY = "eligibility"
    CHARGE_ENTRY = "charge_entry"


# Translation layer only -- maps our readable category vocabulary to the
# real production system's exact CategoryName strings. Used only if/when
# integrating with real data; never referenced during generation itself.
PRODUCTION_CATEGORY_LABEL: dict[TicketCategory, str] = {
    TicketCategory.CLAIMS: "Claims",
    TicketCategory.PAYMENT_POSTING: "Payment Posting",
    TicketCategory.PRIOR_AUTHORIZATION: "PA",
    TicketCategory.ACCOUNTS_RECEIVABLE: "AR",
    TicketCategory.ELIGIBILITY: "Eligibility",
    TicketCategory.CHARGE_ENTRY: "Charge Entry",
}


class TicketStatus(str, enum.Enum):
    """Matches the real production system's 6 states exactly, not just
    OPEN/CLOSED. The retrieval pipeline's "open ticket" scope means
    non-terminal status (see TERMINAL_TICKET_STATUSES below) -- not
    literally status == OPEN, which would wrongly exclude IN_PROGRESS/
    PENDING/WAITING_FOR_CLIENT tickets that are still live and re-matchable.
    """

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING = "PENDING"
    WAITING_FOR_CLIENT = "WAITING_FOR_CLIENT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


TERMINAL_TICKET_STATUSES = frozenset({TicketStatus.RESOLVED, TicketStatus.CLOSED})


class SenderType(str, enum.Enum):
    CLIENT = "client"
    ACCOUNT_MANAGER = "account_manager"


class MessageIntent(str, enum.Enum):
    INITIAL_REQUEST = "initial_request"
    FOLLOW_UP = "follow_up"
    STATUS_CHECK = "status_check"
    DOCUMENTATION_PROVIDED = "documentation_provided"
    THANK_YOU = "thank_you"
    INFORMATIONAL = "informational"


class DifficultyTier(str, enum.Enum):
    EASY = "easy"
    MODERATE_PARAPHRASE = "moderate_paraphrase"
    HARD_SEMANTIC = "hard_semantic"
    HARD_NEGATIVE = "hard_negative"
    BOILERPLATE = "boilerplate"
    SAME_CUSTOMER_DISAMBIGUATION = "same_customer_disambiguation"


class Tone(str, enum.Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"


class LengthBucket(str, enum.Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class NoiseLevel(str, enum.Enum):
    CLEAN = "clean"
    MILD = "mild"
    HEAVY = "heavy"
