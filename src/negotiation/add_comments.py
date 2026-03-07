"""Add standalone comments to a .docx document with two anchoring modes.

Provides add_comments() which creates new comments anchored either to
a tracked change (by Chg:N ID) or to arbitrary text (by text-match).
Follows the validate/resolve/mutate/save pattern established in
accept_changes and counter_propose_changes.

New standalone comments appear in comments.xml with the client author,
have commentRangeStart/End/Reference markers in the document body, and
have a w15:commentEx entry in commentsExtended.xml with done="0".
"""

import re

from docx import Document

from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.author_config import AuthorConfig
from src.models.comment import (
    AddCommentResult,
    AddedComment,
    CommentError,
    FailedComment,
)
from src.negotiation.accept_helpers import validate_output_path
from src.negotiation.add_comment_helpers import (
    anchor_comment_to_text,
    anchor_comment_to_tracked_change,
    create_standalone_comment,
)
from src.negotiation.comment_ids_helpers import (
    get_or_create_comments_extensible_part,
    get_or_create_comments_ids_part,
)
from src.negotiation.reply_helpers import (
    allocate_para_id,
    collect_existing_para_ids,
    get_next_comment_id,
    get_or_create_comments_extended_part,
    get_or_create_comments_part,
)
from src.negotiation.timestamp import generate_timestamp
from src.validation.output_validator import validate_docx_output

CHG_ID_PATTERN = re.compile(r"^Chg:\d+$")
OOXML_ID_PATTERN = re.compile(r"^ooxml:\d+$")


def add_comments(
    input_path: str,
    output_path: str,
    comments: list[tuple[str, str]],
    author_config: AuthorConfig,
) -> AddCommentResult:
    """Add standalone comments to a .docx document.

    Each comment is a (anchor_id, comment_text) tuple where anchor_id
    is either a "Chg:N" string to anchor to a tracked change, an
    "ooxml:NNN" string to anchor directly by OOXML w:id (stable across
    operations), or any other string treated as target text for
    text-match anchoring.

    Resolves all anchors upfront, then applies valid ones. Invalid
    Chg:N anchors are captured in failed_comments rather than aborting
    the entire batch. Com:N anchors still raise (usage error).

    Args:
        input_path: Path to the input .docx document.
        output_path: Path for the output .docx document.
        comments: List of (anchor_id, comment_text) tuples.
        author_config: Client author configuration for attribution.

    Returns:
        AddCommentResult with added comments and any failed comments.

    Raises:
        CommentError: If a Com:N ID is passed (usage error).
    """
    validate_docx_path(input_path)
    _validate_output(output_path)

    state = build_state_of_play(input_path)
    resolutions = _resolve_all_anchors(state, comments)

    document = Document(input_path)
    added, failed = _apply_comments(document, resolutions, author_config)

    validated_path = str(validate_output_path(output_path))
    document.save(validated_path)
    warnings = validate_docx_output(validated_path)
    return AddCommentResult(
        added_comments=added,
        failed_comments=failed,
        validation_warnings=warnings,
    )


def _validate_output(output_path: str) -> None:
    """Validate the output path, re-raising AcceptError as CommentError."""
    from src.models.accept import AcceptError

    try:
        validate_output_path(output_path)
    except AcceptError as exc:
        raise CommentError(str(exc)) from exc


def _resolve_all_anchors(
    state: object,
    comments: list[tuple[str, str]],
) -> list[tuple[str, str, str | None, str | None]]:
    """Resolve all comment anchors and validate upfront.

    Returns list of (anchor_id, comment_text, ooxml_id_or_none, error_or_none)
    tuples. For Chg:N anchors, ooxml_id is resolved from state; if the change
    is not found, error is set. For ooxml:NNN anchors, the raw OOXML w:id is
    used directly (stable across operations). For text anchors, both ooxml_id
    and error are None (validated during XML manipulation).

    Raises:
        CommentError: If a Com:N ID is passed (usage error, not runtime).
    """
    resolutions: list[tuple[str, str, str | None, str | None]] = []

    for anchor_id, comment_text in comments:
        if anchor_id.startswith("Com:"):
            raise CommentError(
                f"Cannot add comment to {anchor_id} -- "
                "use reply_to_comments for comment replies"
            )

        if CHG_ID_PATTERN.match(anchor_id):
            ooxml_id, error = _try_resolve_change_id(state, anchor_id)
            resolutions.append((anchor_id, comment_text, ooxml_id, error))
        elif OOXML_ID_PATTERN.match(anchor_id):
            raw_id = anchor_id.split(":", 1)[1]
            resolutions.append((anchor_id, comment_text, raw_id, None))
        else:
            resolutions.append((anchor_id, comment_text, None, None))

    return resolutions


def _try_resolve_change_id(
    state: object, change_id: str,
) -> tuple[str | None, str | None]:
    """Try to resolve a Chg:N change ID to its ooxml_id from state of play.

    Returns (ooxml_id, None) on success, or (None, error_message) on failure.
    """
    for entry in state.changes:
        if entry.change_id == change_id:
            return entry.ooxml_id, None
    return None, f"Change not found: {change_id}"


def _apply_comments(
    document: Document,
    resolutions: list[tuple[str, str, str | None, str | None]],
    author_config: AuthorConfig,
) -> tuple[list[AddedComment], list[FailedComment]]:
    """Apply resolved comments to the document's XML, skipping failures.

    Comments that failed resolution (error is set) are captured in
    the failed list. Comments that fail during XML anchoring are also
    captured rather than aborting the batch.
    """
    comments_part = get_or_create_comments_part(document)
    extended_part = get_or_create_comments_extended_part(document)
    ids_part = get_or_create_comments_ids_part(document)
    extensible_part = get_or_create_comments_extensible_part(document)
    existing_ids = collect_existing_para_ids(document)
    next_id = get_next_comment_id(comments_part)
    timestamp = generate_timestamp(author_config.date_override)
    body = document.element.body
    added: list[AddedComment] = []
    failed: list[FailedComment] = []

    for anchor_id, comment_text, ooxml_id, error in resolutions:
        if error is not None:
            failed.append(FailedComment(
                anchor_id=anchor_id,
                comment_text=comment_text,
                reason=error,
            ))
            continue

        result = _apply_single_comment(
            body, comments_part, extended_part, existing_ids,
            next_id, author_config, timestamp,
            anchor_id, comment_text, ooxml_id, len(added),
            ids_part=ids_part,
            extensible_part=extensible_part,
        )
        if isinstance(result, AddedComment):
            added.append(result)
        else:
            failed.append(result)
        next_id += 1

    return added, failed


def _apply_single_comment(
    body: object,
    comments_part: object,
    extended_part: object,
    existing_ids: set[str],
    next_id: int,
    author_config: AuthorConfig,
    timestamp: str,
    anchor_id: str,
    comment_text: str,
    ooxml_id: str | None,
    added_count: int,
    ids_part: object | None = None,
    extensible_part: object | None = None,
) -> AddedComment | FailedComment:
    """Apply a single comment, returning AddedComment or FailedComment."""
    try:
        if ooxml_id is not None:
            anchor_comment_to_tracked_change(body, ooxml_id, next_id)
        else:
            anchor_comment_to_text(body, anchor_id, next_id)

        para_id = allocate_para_id(existing_ids, next_id)
        create_standalone_comment(
            comments_part, extended_part, next_id,
            author_config.name, timestamp, comment_text, para_id,
            initials=author_config.initials,
            ids_part=ids_part,
            extensible_part=extensible_part,
        )

        return AddedComment(
            anchor_id=anchor_id,
            comment_text=comment_text,
            comment_id=f"Com:{added_count + 1}",
        )
    except CommentError as exc:
        return FailedComment(
            anchor_id=anchor_id,
            comment_text=comment_text,
            reason=str(exc),
        )
