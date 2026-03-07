"""Negotiation orchestration package.

Provides decision models for Claude's per-change analysis output,
conversion logic to map decisions to pipeline actions, summary building
for supervised mode preview, and entry point functions for full
negotiation and preview.

Configuration is now loaded via src.config.load_config() rather than
hardcoded constants. Test configuration remains available in
src.orchestration.test_config for direct import in tests.

Public API:
    negotiate: Execute full negotiation pipeline with validated decisions.
    preview_negotiation: Preview decisions without document mutation.
    validate_decisions: Validate decision list before execution.
    NegotiationDecision: Claude's decision for a single tracked change.
    DecisionDetail: Single decision detail for supervised mode preview.
    DecisionSummary: Grouped summary of decisions by action type.
    NegotiationResult: Pipeline result wrapped with decision context.
    convert_decisions_to_actions: Map decisions to pipeline actions.
    build_decision_summary: Group decisions for supervised mode preview.
"""

from src.orchestration.decision import (
    DecisionDetail,
    DecisionSummary,
    NegotiationDecision,
    NegotiationResult,
)
from src.orchestration.decision_helpers import (
    convert_decisions_to_actions,
)
from src.orchestration.decision_summary import (
    build_decision_summary,
)
from src.orchestration.negotiator import (
    negotiate,
    preview_negotiation,
)
from src.orchestration.negotiator_helpers import (
    validate_decisions,
)

__all__ = [
    "DecisionDetail",
    "DecisionSummary",
    "NegotiationDecision",
    "NegotiationResult",
    "build_decision_summary",
    "convert_decisions_to_actions",
    "negotiate",
    "preview_negotiation",
    "validate_decisions",
]
