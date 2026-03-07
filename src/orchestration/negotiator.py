"""Negotiation orchestrator entry points.

Provides negotiate() for executing a full negotiation pipeline and
preview_negotiation() for dry-run previews without document mutation.
These are the capstone functions that sit on top of run_pipeline and
convert high-level NegotiationDecision models into mechanical pipeline
actions.

Usage:
    from src.orchestration.negotiator import negotiate, preview_negotiation

    # Full execution -- produces a redlined output document
    result = negotiate(
        input_path="input.docx",
        output_path="output.docx",
        decisions=[NegotiationDecision(...)],
        author_config=AuthorConfig(name="Client Firm"),
    )

    # Preview only -- returns a summary without document mutation
    summary = preview_negotiation(
        input_path="input.docx",
        decisions=[NegotiationDecision(...)],
    )
"""

from src.config.models import NegotiationConfig
from src.ingestion.state_of_play import build_state_of_play
from src.models.author_config import AuthorConfig
from src.orchestration.decision import (
    DecisionSummary,
    NegotiationDecision,
    NegotiationResult,
)
from src.orchestration.decision_helpers import convert_decisions_to_actions
from src.orchestration.decision_summary import build_decision_summary
from src.orchestration.negotiator_helpers import validate_decisions
from src.pipeline.orchestrator import run_pipeline
from src.pipeline.styler import StylerCallback


def negotiate(
    input_path: str,
    output_path: str,
    decisions: list[NegotiationDecision],
    author_config: AuthorConfig,
    styler: StylerCallback | None = None,
    config: NegotiationConfig | None = None,
) -> NegotiationResult:
    """Execute a full negotiation pipeline with validated decisions.

    Orchestrates the complete flow: validate decisions, build state of
    play, convert decisions to pipeline actions, run the pipeline, and
    build a decision summary. Returns a NegotiationResult wrapping the
    pipeline result with full decision context for audit trail.

    Args:
        input_path: Path to the input .docx document with tracked changes.
        output_path: Path for the output .docx document with applied edits.
        decisions: Claude's per-change negotiation decisions.
        author_config: Client author config for tracked change attribution.
        styler: Optional Styler callback for formatting fixes.
        config: Optional NegotiationConfig for audit trail. Not used by the
            pipeline -- by the time negotiate() is called, the LLM has
            already read the config and produced decisions.

    Returns:
        NegotiationResult with pipeline outcomes, decisions, and summary.

    Raises:
        ValueError: If any decision fails validation.
        IngestionError: If input_path is invalid.
        PipelineValidationError: If actions reference invalid IDs.
    """
    validate_decisions(decisions)
    state = build_state_of_play(input_path)
    actions = convert_decisions_to_actions(decisions)
    result = run_pipeline(input_path, output_path, actions, author_config, styler)
    summary = build_decision_summary(decisions, state)
    return NegotiationResult(
        pipeline_result=result,
        decisions=decisions,
        summary=summary,
        config=config,
    )


def preview_negotiation(
    input_path: str,
    decisions: list[NegotiationDecision],
    config: NegotiationConfig | None = None,
) -> DecisionSummary:
    """Preview negotiation decisions without executing the pipeline.

    Validates decisions and builds a structured summary showing what
    would happen for each decision, grouped by action type. No output
    document is created -- this is for supervised mode where the user
    reviews decisions before committing to execution.

    Args:
        input_path: Path to the input .docx document with tracked changes.
        decisions: Claude's per-change negotiation decisions.
        config: Optional NegotiationConfig for API consistency. Not
            currently used in preview mode, but accepted so callers
            can pass config uniformly.

    Returns:
        DecisionSummary with decisions grouped by action type.

    Raises:
        ValueError: If any decision fails validation.
        IngestionError: If input_path is invalid.
    """
    validate_decisions(decisions)
    state = build_state_of_play(input_path)
    return build_decision_summary(decisions, state)
