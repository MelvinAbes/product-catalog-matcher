from enum import StrEnum


class ImportRole(StrEnum):
    REFERENCE = "reference"
    CANDIDATE = "candidate"


class ImportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class IssueSeverity(StrEnum):
    WARNING = "warning"
    ERROR = "error"


class MatchDecision(StrEnum):
    AUTO_MATCH = "auto_match"
    REVIEW = "review"
    NO_MATCH = "no_match"


class ReviewAction(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REASSIGNED = "reassigned"


class RecordStatus(StrEnum):
    VALID = "valid"
    DUPLICATE = "duplicate"
