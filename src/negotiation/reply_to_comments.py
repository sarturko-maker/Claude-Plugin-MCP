"""Reply-to-comments function for threaded comment negotiation.

Provides reply_to_comments() which adds client-attributed threaded replies
to existing counterparty comments. Follows the accept_changes /
counter_propose_changes pattern: validate, resolve IDs, mutate, save.

This is the primary deliverable of Phase 7 / NEG-03 -- enabling lawyers
to reply to counterparty comments with proper threading visible in Word.
"""

from docx import Document

from src.ingestion.comment_loader import load_comments
from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.author_config import AuthorConfig
from src.models.change import TrackedChangeEntry
from src.models.comment import CommentError, CommentReply, ReplyResult
from src.negotiation.accept_helpers import validate_output_path
from src.negotiation.comment_ids_helpers import (
    get_or_create_comments_extensible_part,
    get_or_create_comments_ids_part,
)
from src.negotiation.reply_helpers import (
    add_reply_comment,
    allocate_para_id,
    anchor_reply_to_parent_range,
    collect_existing_para_ids,
    get_next_comment_id,
    get_or_create_comments_extended_part,
    get_or_create_comments_part,
)
from src.negotiation.timestamp import generate_timestamp
from src.validation.output_validator import validate_docx_output


def reply_to_comments(
    input_path: str,
    output_path: str,
    replies: list[tuple[str, str]],
    author_config: AuthorConfig,
) -> ReplyResult:
    """Add threaded replies to existing comments in a .docx document.

    Validates all inputs upfront before any mutation. If any Com:N ID is
    invalid, a Chg:N ID, or nonexistent, raises CommentError with no
    changes applied.
    """
    validate_docx_path(input_path)
    _validate_output(output_path)

    state = build_state_of_play(input_path)
    resolutions = _resolve_all_replies(state, replies)

    document = Document(input_path)
    _apply_replies(document, resolutions, author_config)
    validated_path = str(validate_output_path(output_path))
    document.save(validated_path)
    warnings = validate_docx_output(validated_path)

    return ReplyResult(
        replies=[
            CommentReply(comment_id=com_id, reply_text=text)
            for com_id, text in replies
        ],
        validation_warnings=warnings,
    )


def _validate_output(output_path: str) -> None:
    """Validate output path, re-raising AcceptError as CommentError."""
    from src.models.accept import AcceptError

    try:
        validate_output_path(output_path)
    except AcceptError as exc:
        raise CommentError(str(exc)) from exc


def _resolve_all_replies(
    state: object,
    replies: list[tuple[str, str]],
) -> list[tuple[TrackedChangeEntry, str]]:
    """Resolve all reply targets to (entry, reply_text) pairs.

    Fail-fast: rejects Chg:N IDs and nonexistent Com:N IDs. If any reply
    is invalid, the entire batch is rejected before XML mutation.
    """
    resolutions: list[tuple[TrackedChangeEntry, str]] = []
    for comment_id, reply_text in replies:
        if comment_id.startswith("Chg:"):
            raise CommentError(
                f"Cannot reply to tracked change {comment_id} -- "
                "use Com:N IDs for comment operations"
            )
        entry = _find_comment_entry(state, comment_id)
        if entry is None:
            raise CommentError(f"Comment not found: {comment_id}")
        resolutions.append((entry, reply_text))
    return resolutions


def _find_comment_entry(
    state: object, comment_id: str
) -> TrackedChangeEntry | None:
    """Find a comment entry by Com:N change_id in state of play.

    Searches top-level entries and reply entries nested under parents.
    """
    for entry in state.changes:
        if entry.change_id == comment_id and entry.change_type == "comment":
            return entry
        for reply in entry.replies:
            if reply.change_id == comment_id and reply.change_type == "comment":
                return reply
    return None


def _apply_replies(
    document: Document,
    resolutions: list[tuple[TrackedChangeEntry, str]],
    author_config: AuthorConfig,
) -> None:
    """Apply all resolved replies to the document's comment XML and body anchors."""
    comments_part = get_or_create_comments_part(document)
    extended_part = get_or_create_comments_extended_part(document)
    ids_part = get_or_create_comments_ids_part(document)
    extensible_part = get_or_create_comments_extensible_part(document)
    existing_ids = collect_existing_para_ids(document)
    next_id = get_next_comment_id(comments_part)
    timestamp = generate_timestamp(author_config.date_override)
    comments_lookup = load_comments(document)
    body = document.element.body

    for entry, reply_text in resolutions:
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
        anchor_reply_to_parent_range(body, entry.ooxml_id, next_id)
        next_id += 1


def _get_parent_para_id(
    entry: TrackedChangeEntry,
    comments_lookup: dict[str, dict],
) -> str:
    """Get the paraId of the target comment for thread linkage."""
    comment_data = comments_lookup.get(entry.ooxml_id)
    if not comment_data or not comment_data.get("para_id"):
        raise CommentError(
            f"Cannot find paraId for comment {entry.change_id} "
            f"(ooxml_id={entry.ooxml_id})"
        )
    return comment_data["para_id"]


