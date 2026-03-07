"""In-memory reply operation for the atomic pipeline.

Adds threaded reply comments to a pre-loaded Document object without
any file I/O. The caller provides a Document, pre-resolved
(TrackedChangeEntry, reply_text) pairs, and an AuthorConfig.
This module does NOT call build_state_of_play(), Document(path), or .save().

Reuses comment loading and reply helpers. Returns ActionOutcome records
compatible with the pipeline result model.
"""

from docx.document import Document

from src.ingestion.comment_loader import load_comments
from src.models.author_config import AuthorConfig
from src.models.change import TrackedChangeEntry
from src.models.comment import CommentError
from src.negotiation.comment_ids_helpers import (
    get_or_create_comments_extensible_part,
    get_or_create_comments_ids_part,
)
from src.negotiation.reply_helpers import (
    add_reply_comment,
    allocate_para_id,
    collect_existing_para_ids,
    get_next_comment_id,
    get_or_create_comments_extended_part,
    get_or_create_comments_part,
)
from src.negotiation.timestamp import generate_timestamp
from src.pipeline.results import ActionOutcome


def reply_on_document(
    document: Document,
    resolutions: list[tuple[TrackedChangeEntry, str]],
    author_config: AuthorConfig,
) -> list[ActionOutcome]:
    """Add threaded replies to comments on an in-memory Document.

    For each (entry, reply_text) pair, finds the parent comment's paraId
    and creates a threaded reply in comments.xml and commentsExtended.xml.

    Args:
        document: A pre-loaded python-docx Document object.
        resolutions: List of (TrackedChangeEntry, reply_text) tuples.
        author_config: Client author configuration for attribution.

    Returns:
        List of ActionOutcome records with status for each reply.
    """
    comments_part = get_or_create_comments_part(document)
    extended_part = get_or_create_comments_extended_part(document)
    ids_part = get_or_create_comments_ids_part(document)
    extensible_part = get_or_create_comments_extensible_part(document)
    existing_ids = collect_existing_para_ids(document)
    next_id = get_next_comment_id(comments_part)
    timestamp = generate_timestamp(author_config.date_override)
    comments_lookup = load_comments(document)
    outcomes: list[ActionOutcome] = []

    for entry, reply_text in resolutions:
        try:
            parent_para_id = _get_parent_para_id(entry, comments_lookup)
            para_id = allocate_para_id(existing_ids, next_id)
            add_reply_comment(
                comments_part=comments_part,
                extended_part=extended_part,
                comment_id=next_id,
                author=author_config.name,
                timestamp=timestamp,
                text=reply_text,
                parent_para_id=parent_para_id,
                para_id=para_id,
                initials=author_config.initials,
                ids_part=ids_part,
                extensible_part=extensible_part,
            )
            outcomes.append(ActionOutcome(
                action_type="reply",
                target_id=entry.change_id,
                status="success",
                new_text=reply_text,
            ))
            next_id += 1
        except CommentError as exc:
            outcomes.append(ActionOutcome(
                action_type="reply",
                target_id=entry.change_id,
                status="failed",
                reason=str(exc),
            ))

    return outcomes


def _get_parent_para_id(
    entry: TrackedChangeEntry,
    comments_lookup: dict[str, dict],
) -> str:
    """Get the paraId of the target comment for thread linkage.

    Args:
        entry: The comment entry to reply to.
        comments_lookup: Dictionary of comment data keyed by ooxml_id.

    Returns:
        The paraId string of the target comment.

    Raises:
        CommentError: If the target comment's paraId cannot be found.
    """
    comment_data = comments_lookup.get(entry.ooxml_id)
    if not comment_data or not comment_data.get("para_id"):
        raise CommentError(
            f"Cannot find paraId for comment {entry.change_id} "
            f"(ooxml_id={entry.ooxml_id})"
        )
    return comment_data["para_id"]
