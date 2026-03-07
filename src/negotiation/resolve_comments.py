"""Resolve comment threads by setting w15:done='1' on root commentEx entries.

When given a reply ID, traces the paraIdParent chain to the root before
resolving. Follows validate/resolve/mutate/save.
"""

from docx import Document

from src.ingestion.comment_loader import load_comments, load_comments_extended
from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.change import TrackedChangeEntry
from src.models.comment import CommentError, ResolvedThread, ResolveResult
from src.negotiation.accept_helpers import validate_output_path
from src.negotiation.reply_helpers import (
    W15_NS,
    get_or_create_comments_extended_part,
)
from src.validation.output_validator import validate_docx_output


def resolve_comments(
    input_path: str,
    output_path: str,
    comment_ids: list[str],
) -> ResolveResult:
    """Mark comment threads as resolved by setting w15:done='1' on root.

    If a Com:N ID targets a reply, traces up the thread to the root.
    Validates all IDs upfront before any XML mutation.
    """
    validate_docx_path(input_path)
    _validate_output(output_path)

    state = build_state_of_play(input_path)
    entries = _resolve_all_ids(state, comment_ids)

    document = Document(input_path)
    resolved = _apply_resolutions(document, entries, comment_ids, state)

    validated_path = str(validate_output_path(output_path))
    document.save(validated_path)
    warnings = validate_docx_output(validated_path)
    return ResolveResult(
        resolved_threads=resolved,
        validation_warnings=warnings,
    )


def _validate_output(output_path: str) -> None:
    """Validate the output path, re-raising AcceptError as CommentError."""
    from src.models.accept import AcceptError

    try:
        validate_output_path(output_path)
    except AcceptError as exc:
        raise CommentError(str(exc)) from exc


def _resolve_all_ids(
    state: object,
    comment_ids: list[str],
) -> list[TrackedChangeEntry]:
    """Validate and resolve all Com:N IDs to TrackedChangeEntry objects.

    Fail-fast: rejects Chg:N IDs and nonexistent Com:N IDs before any
    XML mutation.
    """
    entries: list[TrackedChangeEntry] = []
    for comment_id in comment_ids:
        if comment_id.startswith("Chg:"):
            raise CommentError(
                f"Cannot resolve tracked change {comment_id} -- "
                "use Com:N IDs for comment operations"
            )
        entry = _find_comment_entry(state, comment_id)
        if entry is None:
            raise CommentError(f"Comment not found: {comment_id}")
        entries.append(entry)
    return entries


def _find_comment_entry(
    state: object, comment_id: str
) -> TrackedChangeEntry | None:
    """Find a comment entry by Com:N ID, searching top-level and replies."""
    for entry in state.changes:
        if entry.change_id == comment_id and entry.change_type == "comment":
            return entry
        for reply in entry.replies:
            if reply.change_id == comment_id and reply.change_type == "comment":
                return reply
    return None


def _apply_resolutions(
    document: Document,
    entries: list[TrackedChangeEntry],
    original_ids: list[str],
    state: object,
) -> list[ResolvedThread]:
    """Apply all resolutions by setting done='1' on root commentEx entries."""
    comments_lookup = load_comments(document)
    extended_lookup = load_comments_extended(document)
    extended_part = get_or_create_comments_extended_part(document)
    results: list[ResolvedThread] = []

    for entry, original_id in zip(entries, original_ids):
        root_ooxml_id = _trace_to_root_ooxml_id(
            entry, comments_lookup, extended_lookup
        )
        root_com_id = _find_com_id_by_ooxml_id(state, root_ooxml_id)
        _set_done_by_ooxml_id(extended_part, root_ooxml_id, comments_lookup)
        results.append(ResolvedThread(
            comment_id=original_id,
            root_comment_id=root_com_id,
        ))

    return results


def _trace_to_root_ooxml_id(
    entry: TrackedChangeEntry,
    comments_lookup: dict[str, dict],
    extended_lookup: dict[str, dict],
) -> str:
    """Trace up paraIdParent chain to root, returning root's ooxml_id."""
    comment_data = comments_lookup.get(entry.ooxml_id)
    if comment_data is None:
        raise CommentError(f"Comment data not found for {entry.change_id}")

    current_para_id = comment_data["para_id"]
    visited: set[str] = set()

    while current_para_id in extended_lookup:
        if current_para_id in visited:
            break
        visited.add(current_para_id)
        ext_data = extended_lookup[current_para_id]
        parent_para_id = ext_data.get("para_id_parent")
        if parent_para_id is None:
            break
        current_para_id = parent_para_id

    return _find_ooxml_id_by_para_id(current_para_id, comments_lookup)


def _find_ooxml_id_by_para_id(
    para_id: str, comments_lookup: dict[str, dict]
) -> str:
    """Find the ooxml_id (comment ID string) for a comment by its paraId."""
    for ooxml_id, data in comments_lookup.items():
        if data.get("para_id") == para_id:
            return ooxml_id
    raise CommentError(f"No comment found with paraId={para_id}")


def _find_com_id_by_ooxml_id(state: object, ooxml_id: str) -> str:
    """Find the Com:N change_id for a comment by its ooxml_id in state."""
    for entry in state.changes:
        if entry.ooxml_id == ooxml_id and entry.change_type == "comment":
            return entry.change_id
        for reply in entry.replies:
            if reply.ooxml_id == ooxml_id and reply.change_type == "comment":
                return reply.change_id
    return f"Com:{ooxml_id}"


def _set_done_by_ooxml_id(
    extended_part, root_ooxml_id: str, comments_lookup: dict[str, dict]
) -> None:
    """Set w15:done='1' on the root comment's commentEx element."""
    root_data = comments_lookup.get(root_ooxml_id)
    if root_data is None:
        raise CommentError(
            f"Root comment data not found for ooxml_id={root_ooxml_id}"
        )
    root_para_id = root_data["para_id"]
    _set_done_attribute(extended_part, root_para_id)


def _set_done_attribute(extended_part, target_para_id: str) -> None:
    """Find the w15:commentEx by paraId and set done='1'."""
    for entry in extended_part.element:
        if "commentEx" in entry.tag:
            pid = entry.get(f"{{{W15_NS}}}paraId")
            if pid == target_para_id:
                entry.set(f"{{{W15_NS}}}done", "1")
                return
    raise CommentError(
        f"commentEx entry not found for paraId={target_para_id}"
    )
