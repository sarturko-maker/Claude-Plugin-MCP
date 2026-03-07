"""Pipeline package for negotiation action processing.

Provides typed action models, pipeline result models, upfront
validation, group execution, and the pipeline orchestrator entry point.
Actions are the instruction format users provide; results are the
structured output they receive.
"""

from src.pipeline.actions import (
    AcceptAction,
    AddCommentAction,
    CounterProposeAction,
    NegotiationAction,
    ReplyAction,
    ResolveAction,
    sort_actions_by_execution_order,
)
from src.pipeline.executor import execute_action_groups
from src.pipeline.orchestrator import run_pipeline
from src.pipeline.results import (
    ActionOutcome,
    PipelineResult,
    PipelineValidationError,
    StylerReport,
)
from src.pipeline.styler import OoxmlFragment, OoxmlTriplet, StylerCallback
from src.pipeline.styler_extraction import (
    extract_client_triplets,
    splice_corrected_fragments,
)
from src.pipeline.validator import validate_actions_upfront

__all__ = [
    "AcceptAction",
    "AddCommentAction",
    "CounterProposeAction",
    "NegotiationAction",
    "ReplyAction",
    "ResolveAction",
    "sort_actions_by_execution_order",
    "execute_action_groups",
    "run_pipeline",
    "StylerCallback",
    "OoxmlTriplet",
    "OoxmlFragment",
    "extract_client_triplets",
    "splice_corrected_fragments",
    "ActionOutcome",
    "PipelineResult",
    "PipelineValidationError",
    "StylerReport",
    "validate_actions_upfront",
]
