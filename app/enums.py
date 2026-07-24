import enum


class TicketCategory(str, enum.Enum):
    CLAIM_DENIAL = "claim_denial"
    PRIOR_AUTH = "prior_auth"
    PAYMENT_POSTING = "payment_posting"
    DOCUMENTATION_REQUEST = "documentation_request"
    INSURANCE_VERIFICATION = "insurance_verification"
    NEW_SERVICE_REQUEST = "new_service_request"
    GENERAL_ENQUIRY = "general_enquiry"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


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
