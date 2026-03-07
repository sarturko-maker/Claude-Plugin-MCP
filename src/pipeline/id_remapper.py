"""ID remapping utilities for the pipeline executor.

When the pipeline chains operations through temporary files, accepting
tracked changes causes the remaining Chg:N sequential IDs to be
renumbered in the output file. These utilities build mapping tables
and remap action IDs between pipeline steps using stable OOXML w:id
values as the linking key.

Usage:
    from src.pipeline.id_remapper import build_id_to_ooxml_map, remap_remaining_actions

    id_map = build_id_to_ooxml_map(original_state)
    id_map = remap_remaining_actions(remaining_actions, id_map, step_output_path)
"""

from src.ingestion.state_of_play import build_state_of_play
from src.models.change import StateOfPlay
from src.pipeline.actions import NegotiationAction


def build_id_to_ooxml_map(state: StateOfPlay) -> dict[str, str]:
    """Build a mapping from Chg:N and Com:N IDs to OOXML w:id values.

    Walks the state-of-play entries (including replies for comments) and
    maps each change_id to its ooxml_id. This mapping remains stable across
    pipeline steps because OOXML w:id attributes don't change when other
    elements are accepted or counter-proposed.

    Args:
        state: Current state of play.

    Returns:
        Dict mapping "Chg:N" or "Com:N" to ooxml_id string.
    """
    id_map: dict[str, str] = {}
    for entry in state.changes:
        id_map[entry.change_id] = entry.ooxml_id
        _collect_reply_ids(entry.replies, id_map)
    return id_map


def remap_remaining_actions(
    remaining_actions: list[NegotiationAction],
    id_to_ooxml: dict[str, str],
    step_output_path: str,
) -> dict[str, str]:
    """Remap Chg:N and Com:N IDs in remaining actions after a pipeline step.

    After a step that modifies tracked changes (accept, counter-propose),
    the Chg:N sequential numbering in the output file may differ from
    the numbering used by the remaining actions. This function rebuilds
    the state from the output, maps old IDs to new IDs via their stable
    OOXML w:id values, and updates the remaining actions in-place.

    Args:
        remaining_actions: Actions not yet executed (mutated in-place).
        id_to_ooxml: Current change_id → ooxml_id mapping.
        step_output_path: Path to the output file from the last step.

    Returns:
        Updated change_id → ooxml_id mapping reflecting the new state.
    """
    new_state = build_state_of_play(step_output_path)
    new_id_to_ooxml = build_id_to_ooxml_map(new_state)

    ooxml_to_new_id = {
        ooxml_id: new_id for new_id, ooxml_id in new_id_to_ooxml.items()
    }

    for action in remaining_actions:
        _remap_action_ids(action, id_to_ooxml, ooxml_to_new_id)

    return new_id_to_ooxml


def _remap_action_ids(
    action: NegotiationAction,
    id_to_ooxml: dict[str, str],
    ooxml_to_new_id: dict[str, str],
) -> None:
    """Remap all ID fields on a single action in-place.

    Handles change_id (AcceptAction, CounterProposeAction), anchor_id
    (AddCommentAction with Chg: prefix), and comment_id (ReplyAction,
    ResolveAction).
    """
    if hasattr(action, "change_id"):
        action.change_id = _remap_single_id(
            action.change_id, id_to_ooxml, ooxml_to_new_id,
        )

    if hasattr(action, "anchor_id"):
        if action.anchor_id.startswith(("Chg:", "Com:")):
            action.anchor_id = _remap_single_id(
                action.anchor_id, id_to_ooxml, ooxml_to_new_id,
            )

    if hasattr(action, "comment_id"):
        action.comment_id = _remap_single_id(
            action.comment_id, id_to_ooxml, ooxml_to_new_id,
        )


def _remap_single_id(
    old_id: str,
    id_to_ooxml: dict[str, str],
    ooxml_to_new_id: dict[str, str],
) -> str:
    """Remap one ID through the OOXML bridge: old_id → ooxml_id → new_id.

    Returns old_id unchanged if it has no OOXML mapping (unknown ID).
    If the OOXML element was known but no longer exists in the new state
    (e.g. accepted), returns a sentinel ID that will fail downstream
    resolution -- preventing accidental targeting of a renumbered element.
    """
    ooxml_id = id_to_ooxml.get(old_id)
    if ooxml_id is None:
        return old_id

    new_id = ooxml_to_new_id.get(ooxml_id)
    if new_id is None:
        return f"{old_id}:REMOVED"

    return new_id


def _collect_reply_ids(
    replies: list, id_map: dict[str, str]
) -> None:
    """Recursively collect IDs from reply entries."""
    for reply in replies:
        id_map[reply.change_id] = reply.ooxml_id
        if reply.replies:
            _collect_reply_ids(reply.replies, id_map)
