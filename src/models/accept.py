"""Pydantic models and error type for accept-changes operations.

Defines AcceptError for validation and operation failures, AcceptedChange
for recording a single accepted tracked change, and AcceptResult as the
structured return value from accept_changes().
"""

from pydantic import BaseModel


class AcceptError(Exception):
    """Raised when an accept-changes operation fails.

    Covers all failure modes: invalid change IDs, nonexistent changes,
    comment IDs passed to accept, output path validation failures, and
    missing XML elements. A single error type with a descriptive message.
    """


class AcceptedChange(BaseModel):
    """Record of a single accepted tracked change.

    Captures the change_id (Chg:N format), the change_type (insertion
    or deletion), and the text content that was affected by the accept.
    """

    change_id: str
    change_type: str
    text: str


class AcceptResult(BaseModel):
    """Structured result of an accept_changes operation.

    Contains the list of all successfully accepted changes. Returned
    only when all requested changes have been accepted and saved.
    """

    accepted_changes: list[AcceptedChange]
    validation_warnings: list[str] = []
