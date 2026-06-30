from enum import StrEnum


class CompanyLifecycle(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"
    EXCLUDED = "excluded"
    PENDING_REVIEW = "pending_review"


class CompanyType(StrEnum):
    PUBLIC = "public"
    PRE_IPO = "pre_ipo"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class ReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    REJECTED = "rejected"
    INTERESTED = "interested"
    APPLIED = "applied"


class CareerSiteStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"
    UNKNOWN = "unknown"
    SCAN_FAILED = "scan_failed"
    UNSUPPORTED = "unsupported"


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
