"""Decision-to-action conversion.

Converts NegotiationDecision models (Claude's output) into pipeline
NegotiationAction models (pipeline input). Summary building lives in
decision_summary.py (split for the 200-line file limit).
"""

from src.orchestration.decision import (
    NegotiationDecision,
)
from src.pipeline.actions import (
    AcceptAction,
    AddCommentAction,
    CounterProposeAction,
    NegotiationAction,
    ReplyAction,
    ResolveAction,
)


def convert_decisions_to_actions(
    decisions: list[NegotiationDecision],
) -> list[NegotiationAction]:
    """Convert a list of negotiation decisions to pipeline actions.

    Each decision maps to zero or more pipeline actions:
    - accept: AcceptAction + optional AddCommentAction
    - counter_propose: CounterProposeAction + optional AddCommentAction
    - comment: AddCommentAction
    - reply: ReplyAction
    - resolve: ResolveAction
    - no_action: nothing (skipped)

    Args:
        decisions: Claude's per-change decisions.

    Returns:
        Flat list of pipeline actions ready for execution.

    Raises:
        ValueError: If counter_propose decision has empty replacement_text.
    """
    actions: list[NegotiationAction] = []
    for decision in decisions:
        actions.extend(_single_decision_to_actions(decision))
    return actions


def _single_decision_to_actions(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert one negotiation decision to pipeline action(s).

    Handles the mapping from decision action type to the appropriate
    pipeline action model(s). Accept and counter-propose optionally
    produce an AddCommentAction when comment_text is non-empty.

    Args:
        decision: A single negotiation decision.

    Returns:
        List of zero or more pipeline actions.

    Raises:
        ValueError: If counter_propose has empty replacement_text.
    """
    if decision.action == "no_action":
        return []

    if decision.action == "accept":
        return _convert_accept(decision)

    if decision.action == "counter_propose":
        return _convert_counter_propose(decision)

    if decision.action == "comment":
        return _convert_comment(decision)

    if decision.action == "reply":
        return _convert_reply(decision)

    if decision.action == "resolve":
        return _convert_resolve(decision)

    return []


def _convert_accept(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert an accept decision to AcceptAction + optional comment."""
    actions: list[NegotiationAction] = [
        AcceptAction(change_id=decision.change_id)
    ]
    if decision.comment_text:
        actions.append(
            AddCommentAction(
                anchor_id=decision.change_id,
                comment_text=decision.comment_text,
            )
        )
    return actions


def _convert_counter_propose(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert a counter-propose decision to CounterProposeAction + optional comment.

    Raises ValueError if replacement_text is empty.
    """
    if not decision.replacement_text:
        raise ValueError(
            f"counter_propose decision for {decision.change_id} "
            "requires non-empty replacement_text"
        )
    actions: list[NegotiationAction] = [
        CounterProposeAction(
            change_id=decision.change_id,
            replacement_text=decision.replacement_text,
        )
    ]
    if decision.comment_text:
        actions.append(
            AddCommentAction(
                anchor_id=decision.change_id,
                comment_text=decision.comment_text,
            )
        )
    return actions


def _convert_comment(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert a comment decision to AddCommentAction."""
    return [
        AddCommentAction(
            anchor_id=decision.change_id,
            comment_text=decision.comment_text,
        )
    ]


def _convert_reply(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert a reply decision to ReplyAction."""
    return [
        ReplyAction(
            comment_id=decision.change_id,
            reply_text=decision.comment_text,
        )
    ]


def _convert_resolve(
    decision: NegotiationDecision,
) -> list[NegotiationAction]:
    """Convert a resolve decision to ResolveAction."""
    return [
        ResolveAction(comment_id=decision.change_id)
    ]
