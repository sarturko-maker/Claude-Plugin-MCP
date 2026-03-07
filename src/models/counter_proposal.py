"""Pydantic models and error type for counter-proposal operations.

Defines CounterProposalError for validation and operation failures,
CounterProposedChange for recording a single counter-proposal applied,
and CounterProposalResult as the structured return value from
counter_propose_changes().

Counter-proposals layer client-attributed redlines on top of counterparty
markup, preserving the full negotiation audit trail.
"""

from pydantic import BaseModel


class CounterProposalError(Exception):
    """Raised when a counter-proposal operation fails.

    Covers all failure modes: invalid change IDs, nonexistent changes,
    comment IDs passed to counter-propose, empty replacement text on
    deletions, output path validation failures, and missing XML elements.
    """


class CounterProposedChange(BaseModel):
    """Record of a single counter-proposal applied.

    Captures the change_id (Chg:N format), the original text that was
    countered, and the client's proposed replacement text.
    """

    change_id: str
    original_text: str
    replacement_text: str


class CounterProposalResult(BaseModel):
    """Structured result of a counter_propose_changes operation.

    Contains the list of all successfully applied counter-proposals.
    Returned only when all requested counter-proposals have been
    applied and saved to the output document.
    """

    counter_proposals: list[CounterProposedChange]
    validation_warnings: list[str] = []
