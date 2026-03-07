"""Reply comment attachment for state-of-play thread awareness.

Finds reply comments that have no commentReference in the document
body (discovered only through commentsExtended.xml parent/child
linkage) and nests them as TrackedChangeEntry objects in the parent
comment entry's replies list.

Used by state_of_play.py after the document walk to add thread
structure to the flat list of entries.
"""

from src.models.change import TrackedChangeEntry


def attach_reply_comments(
    entries: list[TrackedChangeEntry],
    comments_lookup: dict[str, dict],
    extended_lookup: dict[str, dict],
    comment_counter: int,
) -> None:
    """Attach reply comments to their parent comment entries.

    Reply comments have no commentReference in the document body so
    the walker never sees them. This function finds them via the
    commentsExtended paraIdParent chain and nests them as TrackedChangeEntry
    objects in the parent entry's replies list.

    Mutates entries in place (appends to parent's replies list).

    Args:
        entries: The flat list of tracked change entries from the walker.
        comments_lookup: Comment ID to metadata dict from load_comments.
        extended_lookup: paraId to {para_id_parent, done} from load_comments_extended.
        comment_counter: Current Com:N counter from the walker.
    """
    para_id_to_entry = _build_para_id_index(entries, comments_lookup)
    body_comment_ids = _collect_body_comment_ids(entries)

    for comment_id, comment_data in comments_lookup.items():
        if comment_id in body_comment_ids:
            continue
        para_id = comment_data.get("para_id", "")
        if not para_id or para_id not in extended_lookup:
            continue
        ext_info = extended_lookup[para_id]
        parent_para_id = ext_info.get("para_id_parent")
        if not parent_para_id or parent_para_id not in para_id_to_entry:
            continue

        comment_counter += 1
        reply_entry = TrackedChangeEntry(
            change_id=f"Com:{comment_counter}",
            change_type="comment",
            author=(comment_data.get("author") or "").strip(),
            date=comment_data.get("date") or "",
            paragraph_context="",
            changed_text=comment_data.get("text") or "",
            ooxml_id=comment_id,
        )
        para_id_to_entry[parent_para_id].replies.append(reply_entry)


def _build_para_id_index(
    entries: list[TrackedChangeEntry],
    comments_lookup: dict[str, dict],
) -> dict[str, TrackedChangeEntry]:
    """Map paraId to the TrackedChangeEntry for comment entries.

    Args:
        entries: The flat list of tracked change entries.
        comments_lookup: Comment ID to metadata dict from load_comments.

    Returns:
        Dict mapping paraId string to the corresponding entry.
    """
    index: dict[str, TrackedChangeEntry] = {}
    for entry in entries:
        if entry.change_type != "comment":
            continue
        comment_data = comments_lookup.get(entry.ooxml_id)
        if comment_data:
            para_id = comment_data.get("para_id", "")
            if para_id:
                index[para_id] = entry
    return index


def _collect_body_comment_ids(entries: list[TrackedChangeEntry]) -> set[str]:
    """Collect the ooxml_id values of all comment entries found in the body.

    These are comments that have commentReference in the document and
    were already picked up by the walker. Reply comments (no body
    reference) will not be in this set.

    Args:
        entries: The flat list of tracked change entries.

    Returns:
        Set of comment XML IDs that are already in the entries list.
    """
    return {
        entry.ooxml_id
        for entry in entries
        if entry.change_type == "comment"
    }
