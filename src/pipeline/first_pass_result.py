"""Result models for the first-pass redlining pipeline.

EditOutcome captures the result of a single edit attempt -- whether it
was applied or skipped, with the original edit details preserved for
reporting. RedlineResult aggregates all outcomes with optional Styler
report and output validation warnings.

Usage:
    from src.pipeline.first_pass_result import EditOutcome, RedlineResult

    outcome = EditOutcome(
        target_text="within thirty days",
        new_text="within fourteen days",
        status="applied",
    )
    result = RedlineResult(
        output_path="output.docx",
        applied=[outcome],
        skipped=[],
    )
"""

from typing import Literal

from pydantic import BaseModel

from src.pipeline.results import StylerReport


class EditOutcome(BaseModel):
    """Result of a single edit attempt during first-pass redlining.

    Preserves the original edit details (target_text, new_text, comment)
    alongside the outcome status. Skipped edits include a reason explaining
    why the target_text was not found in the document.

    Attributes:
        target_text: The text the edit was targeting.
        new_text: The replacement text (None for pure deletions).
        comment: Optional comment text attached to the edit.
        status: Whether the edit was applied or skipped.
        reason: Explanation for skipped status. Empty for applied edits.
        method: How the edit was applied. Values:
            '' -- empty for skipped edits or pre-surgical pipeline calls
            'surgical' -- word-level diff applied successfully
            'wholesale' -- delegated to engine.apply_edits()
            'wholesale:multi_paragraph' -- target spans multiple paragraphs
            'wholesale:nested_insert' -- anchored edit fallback
            'anchored:nested_insert' -- layered via apply_anchored_edit
            'wholesale:reconstruction_mismatch' -- safety check failed
            'wholesale:newline_in_new_text' -- new_text contains newline
            'wholesale:pure_deletion' -- pure deletion delegated
    """

    target_text: str
    new_text: str | None = None
    comment: str | None = None
    status: Literal["applied", "skipped"]
    reason: str = ""
    method: str = ""


class RedlineResult(BaseModel):
    """Complete result of a first-pass redlining pipeline execution.

    Contains the output path, per-edit outcomes split into applied and
    skipped lists, optional Styler formatting report, and any OOXML
    validation warnings from the output file.

    Attributes:
        output_path: File path of the redlined output document.
        applied: Edits that were successfully applied as tracked changes.
        skipped: Edits whose target_text was not found in the document.
        styler_report: Formatting correction report if Styler was run.
        validation_warnings: Post-save OOXML validation warnings.
    """

    output_path: str
    applied: list[EditOutcome]
    skipped: list[EditOutcome]
    styler_report: StylerReport | None = None
    validation_warnings: list[str] = []
