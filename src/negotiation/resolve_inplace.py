"""In-memory resolve operation for the atomic pipeline.

Resolves comment threads on a pre-loaded Document object by setting
w15:done='1' on root commentEx entries. The caller provides a Document,
entries, original IDs, and state. This module does NOT call
build_state_of_play(), Document(path), or .save().

Reuses comment_loader for thread tracing and reply_helpers for
commentsExtended part access. Returns ActionOutcome records
compatible with the pipeline result model.
"""

from docx.document import Document

from src.ingestion.comment_loader import load_comments, load_comments_extended
from src.models.change import StateOfPlay, TrackedChangeEntry
from src.models.comment import CommentError
from src.negotiation.reply_helpers import (
    W15_NS,
    get_or_create_comments_extended_part,
)
from src.pipeline.results import ActionOutcome


def resolve_on_document(
    document: Document,
    entries: list[TrackedChangeEntry],
    original_ids: list[str],
    state: StateOfPlay,
) -> list[ActionOutcome]:
    """Resolve comment threads on an in-memory Document.

    For each entry, traces the paraIdParent chain to the root comment,
    then sets w15:done='1' on the root's commentEx element.

    Args:
        document: A pre-loaded python-docx Document object.
        entries: List of TrackedChangeEntry objects for comments to resolve.
        original_ids: List of original Com:N IDs (parallel to entries).
        state: The document's StateOfPlay for Com:N ID lookup.

    Returns:
        List of ActionOutcome records with status for each resolution.
    """
    comments_lookup = load_comments(document)
    extended_lookup = load_comments_extended(document)
    extended_part = get_or_create_comments_extended_part(document)
    outcomes: list[ActionOutcome] = []

    for entry, original_id in zip(entries, original_ids):
        try:
            root_ooxml_id = _trace_to_root_ooxml_id(
                entry, comments_lookup, extended_lookup
            )
            _set_done_by_ooxml_id(extended_part, root_ooxml_id, comments_lookup)
            outcomes.append(ActionOutcome(
                action_type="resolve",
                target_id=original_id,
                status="success",
            ))
        except CommentError as exc:
            outcomes.append(ActionOutcome(
                action_type="resolve",
                target_id=original_id,
                status="failed",
                reason=str(exc),
            ))

    return outcomes


def _trace_to_root_ooxml_id(
    entry: TrackedChangeEntry,
    comments_lookup: dict[str, dict],
    extended_lookup: dict[str, dict],
) -> str:
    """Trace up the paraIdParent chain to the root comment's ooxml_id.

    Starting from the entry's comment, follows paraIdParent links until
    reaching a comment with no parent (the thread root).

    Args:
        entry: The comment entry to trace from.
        comments_lookup: Comments indexed by ooxml_id.
        extended_lookup: CommentsExtended indexed by paraId.

    Returns:
        The ooxml_id of the root comment in the thread.

    Raises:
        CommentError: If comment data is missing.
    """
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
    """Find the ooxml_id for a comment by its paraId.

    Args:
        para_id: The paraId to look up.
        comments_lookup: Comments indexed by ooxml_id.

    Returns:
        The matching ooxml_id string.

    Raises:
        CommentError: If no comment has the given paraId.
    """
    for ooxml_id, data in comments_lookup.items():
        if data.get("para_id") == para_id:
            return ooxml_id
    raise CommentError(f"No comment found with paraId={para_id}")


def _set_done_by_ooxml_id(
    extended_part: object,
    root_ooxml_id: str,
    comments_lookup: dict[str, dict],
) -> None:
    """Set w15:done='1' on the root comment's commentEx element.

    Args:
        extended_part: The commentsExtended OPC part.
        root_ooxml_id: The ooxml_id of the root comment.
        comments_lookup: Comments indexed by ooxml_id.

    Raises:
        CommentError: If the root comment data or commentEx entry is missing.
    """
    root_data = comments_lookup.get(root_ooxml_id)
    if root_data is None:
        raise CommentError(
            f"Root comment data not found for ooxml_id={root_ooxml_id}"
        )
    root_para_id = root_data["para_id"]

    for entry in extended_part.element:
        if "commentEx" in entry.tag:
            pid = entry.get(f"{{{W15_NS}}}paraId")
            if pid == root_para_id:
                entry.set(f"{{{W15_NS}}}done", "1")
                return

    raise CommentError(
        f"commentEx entry not found for paraId={root_para_id}"
    )
