"""Upfront validation of negotiation actions against document state.

Validates all action references, detects duplicates, and catches
conflicting actions BEFORE any XML mutation begins. This is the
fail-fast layer -- if validation fails, no changes are made to the
document. Edit-time failures are handled separately by the pipeline
orchestrator with skip-and-continue.

Usage:
    from src.pipeline.validator import validate_actions_upfront

    validate_actions_upfront(actions, state_of_play)
    # Raises PipelineValidationError if any issues found
"""

from src.models.change import StateOfPlay, TrackedChangeEntry
from src.pipeline.actions import (
    AcceptAction,
    AddCommentAction,
    CounterProposeAction,
    NegotiationAction,
    ReplyAction,
    ResolveAction,
)
from src.pipeline.results import PipelineValidationError


def validate_actions_upfront(
    actions: list[NegotiationAction], state: StateOfPlay
) -> None:
    """Validate all actions against the current state of play.

    Collects ALL validation errors before raising, so the caller
    sees every problem at once. Checks:
    1. All Chg:N IDs exist in state.changes
    2. All Com:N IDs exist in state.changes (including nested replies)
    3. AddCommentAction anchor_ids starting with "Chg:" exist
    4. No duplicate target IDs within the same action type
    5. No conflicting actions (accept + counter-propose on same ID)

    Raises:
        PipelineValidationError: If any validation errors are found.
    """
    errors: list[str] = []
    change_ids = _collect_all_change_ids(state)
    comment_ids = _collect_all_comment_ids(state)

    _check_id_existence(actions, change_ids, comment_ids, errors)
    _check_duplicates(actions, errors)
    _check_conflicts(actions, errors)
    _check_replacement_text(actions, errors)

    if errors:
        raise PipelineValidationError(errors=errors)


def _collect_all_change_ids(state: StateOfPlay) -> set[str]:
    """Collect all Chg:N IDs from the state of play changes."""
    return {
        entry.change_id
        for entry in state.changes
        if entry.change_id.startswith("Chg:")
    }


def _collect_all_comment_ids(state: StateOfPlay) -> set[str]:
    """Walk changes and their replies to collect all Com:N IDs.

    Comments can be nested -- a reply has its own change_id and may
    contain further replies. This recursively walks the tree.
    """
    comment_ids: set[str] = set()
    _walk_comment_tree(state.changes, comment_ids)
    return comment_ids


def _walk_comment_tree(
    entries: list[TrackedChangeEntry], collected: set[str]
) -> None:
    """Recursively collect Com:N IDs from entries and their replies."""
    for entry in entries:
        if entry.change_id.startswith("Com:"):
            collected.add(entry.change_id)
        if entry.replies:
            _walk_comment_tree(entry.replies, collected)


def _check_id_existence(
    actions: list[NegotiationAction],
    change_ids: set[str],
    comment_ids: set[str],
    errors: list[str],
) -> None:
    """Check that all referenced IDs exist in the state of play."""
    for action in actions:
        if isinstance(action, (AcceptAction, CounterProposeAction)):
            if action.change_id not in change_ids:
                errors.append(
                    f"Change ID {action.change_id} does not exist in document"
                )
        elif isinstance(action, (ReplyAction, ResolveAction)):
            if action.comment_id not in comment_ids:
                errors.append(
                    f"Comment ID {action.comment_id} does not exist in document"
                )
        elif isinstance(action, AddCommentAction):
            if action.anchor_id.startswith("Chg:"):
                if action.anchor_id not in change_ids:
                    errors.append(
                        f"Anchor ID {action.anchor_id} does not exist in document"
                    )


def _check_duplicates(
    actions: list[NegotiationAction], errors: list[str]
) -> None:
    """Check for duplicate target IDs within the same action type."""
    seen_by_type: dict[str, set[str]] = {}

    for action in actions:
        target_id = _get_target_id(action)
        action_type = action.action_type

        if action_type not in seen_by_type:
            seen_by_type[action_type] = set()

        if target_id in seen_by_type[action_type]:
            errors.append(
                f"Duplicate {action_type} action for {target_id}"
            )
        else:
            seen_by_type[action_type].add(target_id)


def _check_conflicts(
    actions: list[NegotiationAction], errors: list[str]
) -> None:
    """Check for conflicting actions on the same target.

    An accept and a counter-propose on the same change_id is a conflict --
    you cannot both accept and counter-propose the same change.
    """
    accept_ids: set[str] = set()
    counter_propose_ids: set[str] = set()

    for action in actions:
        if isinstance(action, AcceptAction):
            accept_ids.add(action.change_id)
        elif isinstance(action, CounterProposeAction):
            counter_propose_ids.add(action.change_id)

    conflicts = accept_ids & counter_propose_ids
    for conflict_id in sorted(conflicts):
        errors.append(
            f"Conflict: {conflict_id} has both accept and counter-propose actions"
        )


def _check_replacement_text(
    actions: list[NegotiationAction], errors: list[str]
) -> None:
    """Check that counter_propose actions have non-empty replacement_text.

    The Pydantic validator on CounterProposeAction catches this at
    construction time, but this check provides a safety net for actions
    built via model_construct and ensures the error appears in the
    collect-all-errors output.
    """
    for action in actions:
        if isinstance(action, CounterProposeAction):
            if not action.replacement_text.strip():
                errors.append(
                    f"{action.change_id}: counter_propose requires "
                    f"non-empty replacement_text"
                )


def _get_target_id(action: NegotiationAction) -> str:
    """Extract the target ID from any action type."""
    if isinstance(action, (AcceptAction, CounterProposeAction)):
        return action.change_id
    elif isinstance(action, (ReplyAction, ResolveAction)):
        return action.comment_id
    elif isinstance(action, AddCommentAction):
        return action.anchor_id
    return ""
