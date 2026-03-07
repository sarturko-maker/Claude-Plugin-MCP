"""Resolution helpers for the pipeline group executor.

Provides resolver functions that translate typed action lists into the
argument format each in-memory negotiation operation expects. Each resolver
looks up the action's target ID in id_to_ooxml to find the stable ooxml_id,
then finds the matching TrackedChangeEntry in state.changes by ooxml_id.

Also provides build_failed_outcomes for the skip-and-continue error pattern.

Split from executor.py to keep both modules under 200 lines per
CLAUDE.md conventions.
"""

from src.models.change import StateOfPlay, TrackedChangeEntry
from src.pipeline.actions import NegotiationAction
from src.pipeline.results import ActionOutcome


def resolve_accept_group(
    actions: list[NegotiationAction],
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
) -> list[TrackedChangeEntry]:
    """Resolve accept actions to TrackedChangeEntry list via ooxml_id lookup.

    For each action, finds the stable ooxml_id from id_to_ooxml, then
    locates the matching TrackedChangeEntry in state.changes.

    Args:
        actions: Accept actions with change_id fields.
        state: Document state of play with all entries.
        id_to_ooxml: Mapping from Chg:N/Com:N to stable ooxml_id.

    Returns:
        List of TrackedChangeEntry objects to accept.
    """
    entries_by_ooxml = _build_entries_by_ooxml(state)
    result: list[TrackedChangeEntry] = []
    for action in actions:
        entry = _resolve_entry(action.change_id, id_to_ooxml, entries_by_ooxml)
        if entry is not None:
            result.append(entry)
    return result


def resolve_counter_propose_group(
    actions: list[NegotiationAction],
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
) -> list[tuple[TrackedChangeEntry, str]]:
    """Resolve counter-propose actions to (entry, replacement_text) pairs.

    Args:
        actions: Counter-propose actions with change_id and replacement_text.
        state: Document state of play with all entries.
        id_to_ooxml: Mapping from Chg:N/Com:N to stable ooxml_id.

    Returns:
        List of (TrackedChangeEntry, replacement_text) tuples.
    """
    entries_by_ooxml = _build_entries_by_ooxml(state)
    result: list[tuple[TrackedChangeEntry, str]] = []
    for action in actions:
        entry = _resolve_entry(action.change_id, id_to_ooxml, entries_by_ooxml)
        if entry is not None:
            result.append((entry, action.replacement_text))
    return result


def resolve_add_comment_group(
    actions: list[NegotiationAction],
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
) -> list[tuple[str, str, str | None, str | None]]:
    """Resolve add-comment actions to (anchor_id, text, ooxml_id, error) tuples.

    For Chg:-prefixed anchor_ids, resolves ooxml_id from the map. For
    text-match anchors, passes through with ooxml_id=None. Pre-failed
    anchors (e.g. REMOVED sentinels) get an error string.

    Args:
        actions: Add-comment actions with anchor_id and comment_text.
        state: Document state of play (for ooxml_id resolution).
        id_to_ooxml: Mapping from Chg:N/Com:N to stable ooxml_id.

    Returns:
        List of (anchor_id, comment_text, ooxml_id_or_none, error_or_none).
    """
    result: list[tuple[str, str, str | None, str | None]] = []
    for action in actions:
        anchor_id = action.anchor_id
        if anchor_id.startswith(("Chg:", "Com:")):
            if ":REMOVED" in anchor_id:
                result.append((
                    anchor_id, action.comment_text, None,
                    f"Anchor {anchor_id} was removed by a prior operation",
                ))
            else:
                ooxml_id = id_to_ooxml.get(anchor_id)
                if ooxml_id is None:
                    result.append((
                        anchor_id, action.comment_text, None,
                        f"No ooxml_id found for {anchor_id}",
                    ))
                else:
                    result.append((
                        anchor_id, action.comment_text, ooxml_id, None,
                    ))
        else:
            # Text-match anchor -- no ooxml_id needed
            result.append((anchor_id, action.comment_text, None, None))
    return result


def resolve_reply_group(
    actions: list[NegotiationAction],
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
) -> list[tuple[TrackedChangeEntry, str]]:
    """Resolve reply actions to (TrackedChangeEntry, reply_text) pairs.

    Searches both top-level changes and nested replies for matching entries.

    Args:
        actions: Reply actions with comment_id and reply_text.
        state: Document state of play with all entries.
        id_to_ooxml: Mapping from Com:N to stable ooxml_id.

    Returns:
        List of (TrackedChangeEntry, reply_text) tuples.
    """
    all_entries = _build_all_entries_by_ooxml(state)
    result: list[tuple[TrackedChangeEntry, str]] = []
    for action in actions:
        entry = _resolve_entry(action.comment_id, id_to_ooxml, all_entries)
        if entry is not None:
            result.append((entry, action.reply_text))
    return result


def resolve_resolve_group(
    actions: list[NegotiationAction],
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
) -> tuple[list[TrackedChangeEntry], list[str]]:
    """Resolve resolve actions to (entries, original_ids) pair.

    Args:
        actions: Resolve actions with comment_id.
        state: Document state of play with all entries.
        id_to_ooxml: Mapping from Com:N to stable ooxml_id.

    Returns:
        Tuple of (entries list, original_id list) in parallel order.
    """
    all_entries = _build_all_entries_by_ooxml(state)
    entries: list[TrackedChangeEntry] = []
    original_ids: list[str] = []
    for action in actions:
        entry = _resolve_entry(action.comment_id, id_to_ooxml, all_entries)
        if entry is not None:
            entries.append(entry)
            original_ids.append(action.comment_id)
    return entries, original_ids


def build_failed_outcomes(
    actions: list[NegotiationAction],
    error: Exception,
) -> list[ActionOutcome]:
    """Build failed ActionOutcome records for all actions in a group.

    Used when an entire group fails. Each action gets a failed
    outcome with the error message as the reason.
    """
    reason = str(error)
    outcomes: list[ActionOutcome] = []
    for action in actions:
        target_id = _get_target_id_from_action(action)
        outcomes.append(ActionOutcome(
            action_type=action.action_type,
            target_id=target_id,
            status="failed",
            reason=reason,
        ))
    return outcomes


def _build_entries_by_ooxml(state: StateOfPlay) -> dict[str, TrackedChangeEntry]:
    """Build a lookup from ooxml_id to TrackedChangeEntry (tracked changes only).

    Excludes comment entries because comment ooxml_ids come from a different
    XML namespace (comments.xml w:id) than tracked change ooxml_ids (document
    body w:id). These IDs can collide numerically, so mixing them in the same
    lookup causes accept/counter-propose operations to target comment entries
    instead of tracked change elements.
    """
    return {
        entry.ooxml_id: entry
        for entry in state.changes
        if entry.ooxml_id and entry.change_type != "comment"
    }


def _build_all_entries_by_ooxml(
    state: StateOfPlay,
) -> dict[str, TrackedChangeEntry]:
    """Build a lookup from ooxml_id to TrackedChangeEntry including replies."""
    result: dict[str, TrackedChangeEntry] = {}
    for entry in state.changes:
        if entry.ooxml_id:
            result[entry.ooxml_id] = entry
        _collect_replies(entry.replies, result)
    return result


def _collect_replies(
    replies: list[TrackedChangeEntry],
    result: dict[str, TrackedChangeEntry],
) -> None:
    """Recursively collect reply entries into the lookup."""
    for reply in replies:
        if reply.ooxml_id:
            result[reply.ooxml_id] = reply
        if reply.replies:
            _collect_replies(reply.replies, result)


def _resolve_entry(
    action_id: str,
    id_to_ooxml: dict[str, str],
    entries_by_ooxml: dict[str, TrackedChangeEntry],
) -> TrackedChangeEntry | None:
    """Resolve an action ID to a TrackedChangeEntry via ooxml_id bridge.

    Returns None if the ooxml_id is unknown or no entry matches.
    """
    ooxml_id = id_to_ooxml.get(action_id)
    if ooxml_id is None:
        return None
    return entries_by_ooxml.get(ooxml_id)


def _get_target_id_from_action(action: NegotiationAction) -> str:
    """Extract the target ID from any action type."""
    if hasattr(action, "change_id"):
        return action.change_id
    if hasattr(action, "comment_id"):
        return action.comment_id
    if hasattr(action, "anchor_id"):
        return action.anchor_id
    return ""
