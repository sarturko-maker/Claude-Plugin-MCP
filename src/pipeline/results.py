"""Pipeline result models for structured output reporting.

ActionOutcome captures the result of a single action (success, skipped,
or failed) with optional before/after text diffs. StylerReport summarizes
formatting corrections applied by the Styler step. PipelineResult
aggregates all outcomes into a single structured response.

PipelineValidationError is raised by upfront validation when the action
list contains invalid references, duplicates, or conflicts.
"""

from typing import Literal

from pydantic import BaseModel


class ActionOutcome(BaseModel):
    """Result of executing a single negotiation action.

    Attributes:
        action_type: Type of action executed (e.g. "accept", "counter_propose").
        target_id: ID of the change or comment targeted (e.g. "Chg:1", "Com:3").
        status: Whether the action succeeded, was skipped, or failed.
        reason: Explanation for skipped/failed status. Empty for success.
        original_text: Text before the action was applied. Empty if not applicable.
        new_text: Text after the action was applied. Empty if not applicable.
        method: How the action was applied (e.g. "surgical", "wholesale"). Empty
            for non-counter-propose actions or when not applicable.
    """

    action_type: str
    target_id: str
    status: Literal["success", "skipped", "failed"]
    reason: str = ""
    original_text: str = ""
    new_text: str = ""
    method: str = ""


class StylerReport(BaseModel):
    """Summary of formatting corrections applied by the Styler step.

    Attributes:
        triplets_extracted: Number of paragraph triplets extracted for review.
        triplets_corrected: Number of triplets that needed formatting fixes.
        details: Per-triplet descriptions of what was corrected.
    """

    triplets_extracted: int
    triplets_corrected: int
    details: list[str] = []


class PipelineResult(BaseModel):
    """Complete result of a pipeline execution.

    Attributes:
        output_path: File path of the output .docx document.
        outcomes: Per-action results with status and optional text diffs.
        summary: Counts by category (accepted, counter_proposed, commented,
            replied, resolved, skipped, failed).
        styler_report: Optional formatting correction report from Styler step.
        validation_warnings: Post-save OOXML validation warnings.
    """

    output_path: str
    outcomes: list[ActionOutcome]
    summary: dict[str, int]
    styler_report: StylerReport | None = None
    validation_warnings: list[str] = []


class PipelineValidationError(Exception):
    """Raised when upfront validation finds invalid actions.

    Collects all validation errors before raising, so the caller
    sees every problem at once rather than fixing them one at a time.

    Attributes:
        errors: List of validation error descriptions.
    """

    def __init__(self, errors: list[str]) -> None:
        """Initialize with a list of validation error descriptions."""
        self.errors = errors
        super().__init__("\n".join(errors))
