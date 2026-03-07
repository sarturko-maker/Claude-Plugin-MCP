"""Decision summary building for supervised mode preview.

Groups NegotiationDecisions by action type and looks up change context
from the state of play for human-readable descriptions. Split from
decision_helpers.py for the 200-line file limit.
"""

from src.models.change import StateOfPlay
from src.orchestration.decision import (
    DecisionDetail,
    DecisionSummary,
    NegotiationDecision,
)


def build_decision_summary(
    decisions: list[NegotiationDecision],
    state: StateOfPlay,
) -> DecisionSummary:
    """Build a grouped summary of decisions for supervised mode preview.

    Groups decisions by action type and looks up change context from
    the state of play for human-readable descriptions.

    Args:
        decisions: Claude's per-change decisions.
        state: Document state of play with change details.

    Returns:
        DecisionSummary with decisions grouped by action type.
    """
    change_lookup = _build_change_lookup(state)

    summary = DecisionSummary(total_changes=len(state.changes))

    for decision in decisions:
        detail = _build_detail(decision, change_lookup)
        _append_detail_to_summary(summary, decision.action, detail)

    return summary


def _build_change_lookup(state: StateOfPlay) -> dict[str, str]:
    """Build a lookup from change_id to a brief text summary."""
    lookup: dict[str, str] = {}
    for change in state.changes:
        text = change.changed_text[:80] if change.changed_text else ""
        lookup[change.change_id] = f"{change.change_type}: {text}"
    return lookup


def _build_detail(
    decision: NegotiationDecision,
    change_lookup: dict[str, str],
) -> DecisionDetail:
    """Create a DecisionDetail from a decision and change lookup."""
    return DecisionDetail(
        change_id=decision.change_id,
        change_summary=change_lookup.get(decision.change_id, "Unknown"),
        action=decision.action,
        reasoning=decision.reasoning,
        replacement_text=decision.replacement_text,
        comment_text=decision.comment_text,
    )


def _append_detail_to_summary(
    summary: DecisionSummary,
    action: str,
    detail: DecisionDetail,
) -> None:
    """Append a DecisionDetail to the appropriate summary list."""
    action_to_list = {
        "accept": summary.accepts,
        "counter_propose": summary.counter_proposals,
        "comment": summary.comments,
        "reply": summary.replies,
        "resolve": summary.resolves,
        "no_action": summary.no_actions,
    }
    target_list = action_to_list.get(action)
    if target_list is not None:
        target_list.append(detail)
