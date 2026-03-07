"""Pipeline orchestrator -- single entry point for all negotiation operations.

Provides run_pipeline() which validates inputs, sorts actions, loads the
Document once, executes all operations in memory, cleans empty w:ins
elements, saves once, and returns a structured PipelineResult.

This is the atomic single-pass executor: one Document load, all mutations
in memory, one save. No intermediate files, no re-ingestion.

Usage:
    from src.pipeline.orchestrator import run_pipeline

    result = run_pipeline(
        input_path="input.docx",
        output_path="output.docx",
        actions=[AcceptAction(change_id="Chg:1"), ...],
        author_config=AuthorConfig(name="Client Firm"),
    )
"""

import shutil
from pathlib import Path

from docx import Document

from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.author_config import AuthorConfig
from src.pipeline.actions import NegotiationAction, sort_actions_by_execution_order
from src.pipeline.empty_ins_cleaner import clean_empty_ins_elements
from src.pipeline.executor import execute_action_groups
from src.pipeline.results import ActionOutcome, PipelineResult, StylerReport
from src.pipeline.styler import StylerCallback
from src.pipeline.styler_extraction import (
    extract_client_triplets,
    splice_corrected_fragments,
)
from src.pipeline.validator import validate_actions_upfront
from src.validation.output_validator import validate_docx_output


def run_pipeline(
    input_path: str,
    output_path: str,
    actions: list[NegotiationAction],
    author_config: AuthorConfig,
    styler: StylerCallback | None = None,
) -> PipelineResult:
    """Execute the full negotiation pipeline atomically.

    Validates inputs, sorts actions, loads the Document once, executes
    all operation groups in memory, cleans empty w:ins elements, saves
    once, and returns a structured result. No intermediate files are
    created during execution.

    Args:
        input_path: Path to the input .docx document.
        output_path: Path for the output .docx document.
        actions: List of typed negotiation actions.
        author_config: Client author config for attribution.
        styler: Optional Styler callback for formatting fixes.

    Returns:
        PipelineResult with per-action outcomes and summary.

    Raises:
        IngestionError: If input_path is invalid.
        PipelineValidationError: If actions reference invalid IDs.
        ValueError: If output_path is invalid.
    """
    validate_docx_path(input_path)
    _validate_output_path(output_path)

    if not actions:
        shutil.copy2(input_path, output_path)
        return PipelineResult(
            output_path=output_path, outcomes=[], summary={},
        )

    state = build_state_of_play(input_path)
    validate_actions_upfront(actions, state)
    sorted_actions = sort_actions_by_execution_order(actions)

    document = Document(input_path)
    outcomes = execute_action_groups(
        document, state, sorted_actions, author_config,
    )
    clean_empty_ins_elements(document.element.body)
    document.save(output_path)

    styler_report: StylerReport | None = None
    if styler is not None:
        styler_report = _run_styler_step(
            output_path, author_config.name, styler,
        )

    warnings = validate_docx_output(output_path)
    summary = _build_summary(outcomes)

    return PipelineResult(
        output_path=output_path,
        outcomes=outcomes,
        summary=summary,
        styler_report=styler_report,
        validation_warnings=warnings,
    )


def _run_styler_step(
    output_path: str,
    client_author: str,
    styler: StylerCallback,
) -> StylerReport:
    """Run the Styler extraction/correction/splicing step.

    Extracts client-authored paragraphs as OOXML triplets, passes them
    to the external StylerCallback for formatting correction, and splices
    corrected fragments back into the document in-place.

    Args:
        output_path: Path to the output .docx document (modified in-place).
        client_author: Client author name for extraction matching.
        styler: External callback that corrects OOXML formatting.

    Returns:
        StylerReport summarizing extraction and correction counts.
    """
    triplets = extract_client_triplets(output_path, client_author)
    fragments = []

    if triplets:
        fragments = styler.fix_formatting(triplets)
        if fragments:
            splice_corrected_fragments(output_path, output_path, fragments)

    return StylerReport(
        triplets_extracted=len(triplets),
        triplets_corrected=len(fragments),
        details=[
            f"Corrected paragraph at index {f.paragraph_index}"
            for f in fragments
        ],
    )


def _validate_output_path(output_path: str) -> None:
    """Validate the output path for the pipeline result.

    Checks that the path ends with .docx, the parent directory exists,
    and there is no path traversal attempt.

    Raises:
        ValueError: If the output path is invalid.
    """
    path = Path(output_path)

    raw_parts = Path(output_path).parts
    if ".." in raw_parts:
        raise ValueError("Invalid output path: path traversal detected")

    if path.suffix.lower() != ".docx":
        raise ValueError("Output path must end with .docx")

    if not path.parent.exists():
        raise ValueError(
            f"Output directory does not exist: {path.parent.name}"
        )


def _build_summary(outcomes: list[ActionOutcome]) -> dict[str, int]:
    """Build a summary dict counting outcomes by action_type and status.

    Returns counts like: {"accept_success": 2, "counter_propose_failed": 1}
    """
    summary: dict[str, int] = {}
    for outcome in outcomes:
        key = f"{outcome.action_type}_{outcome.status}"
        summary[key] = summary.get(key, 0) + 1
    return summary
