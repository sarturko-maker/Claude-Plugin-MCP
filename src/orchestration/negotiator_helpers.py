"""Validation helpers for the negotiation orchestrator.

Validates NegotiationDecision lists before pipeline execution.
Fail-fast validation catches invalid decisions (e.g., counter-propose
without replacement text) before any document mutation occurs.
"""

from src.orchestration.decision import NegotiationDecision


def validate_decisions(decisions: list[NegotiationDecision]) -> None:
    """Validate a list of negotiation decisions for correctness.

    Checks that required fields are populated for each action type:
    - counter_propose: must have non-empty replacement_text
    - comment: must have non-empty comment_text
    - reply: must have non-empty comment_text

    Args:
        decisions: List of negotiation decisions to validate.

    Returns:
        None on success.

    Raises:
        ValueError: If any decision fails validation, with a descriptive
            message identifying the problematic decision and field.
    """
    for decision in decisions:
        _validate_single_decision(decision)


def _validate_single_decision(decision: NegotiationDecision) -> None:
    """Validate a single negotiation decision for required fields.

    Args:
        decision: A single negotiation decision.

    Raises:
        ValueError: If required fields are missing for the action type.
    """
    if decision.action == "counter_propose" and not decision.replacement_text:
        raise ValueError(
            f"counter_propose decision for {decision.change_id} "
            "requires non-empty replacement_text"
        )

    if decision.action == "comment" and not decision.comment_text:
        raise ValueError(
            f"comment decision for {decision.change_id} "
            "requires non-empty comment_text"
        )

    if decision.action == "reply" and not decision.comment_text:
        raise ValueError(
            f"reply decision for {decision.change_id} "
            "requires non-empty comment_text"
        )
