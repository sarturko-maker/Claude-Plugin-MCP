"""Result models for batch edit operations with skip-on-failure.

Provides typed data contracts for capturing per-edit success/failure
information when applying multiple negotiation operations. Used by
Phase 9 pipeline to continue processing remaining edits when one fails.

EditFailure records a single edit that could not be applied.
BatchEditResult aggregates successes, failures, and post-save
validation warnings from validate_docx_output.

Usage:
    from src.models.edit_result import EditFailure, BatchEditResult

    failure = EditFailure(
        edit_id="Chg:1",
        operation="accept",
        reason="Change not found in document",
    )
    result = BatchEditResult(
        successes=["Chg:2", "Chg:3"],
        failures=[failure],
        validation_warnings=[],
    )
"""

from pydantic import BaseModel


class EditFailure(BaseModel):
    """Record of a single edit that failed to apply.

    Attributes:
        edit_id: Identifier of the edit (e.g. 'Chg:1', 'Com:3').
        operation: Type of operation attempted ('accept', 'counter_propose',
            'comment', 'reply', 'resolve').
        reason: Human-readable description of why the edit failed.
    """

    edit_id: str
    operation: str
    reason: str


class BatchEditResult(BaseModel):
    """Result of applying multiple edits with skip-on-failure.

    Attributes:
        successes: List of edit IDs that were applied successfully.
        failures: List of EditFailure records for edits that could not
            be applied.
        validation_warnings: Post-save OOXML validation warnings from
            validate_docx_output. Empty list means structurally valid.
    """

    successes: list[str]
    failures: list[EditFailure]
    validation_warnings: list[str]
