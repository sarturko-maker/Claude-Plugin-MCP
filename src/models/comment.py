"""Pydantic models and error type for comment operations.

Defines models for the three comment operations in Phase 7:
reply to existing comments, add new standalone comments, and
resolve comment threads. Each operation has a record model for
individual items and a result model for the batch outcome.

Follows the same pattern as accept.py and counter_proposal.py.
"""

from pydantic import BaseModel


class CommentError(Exception):
    """Raised when a comment operation fails.

    Covers all failure modes across reply, add, and resolve operations:
    invalid Com:N or Chg:N IDs, nonexistent targets, output path
    validation failures, and missing XML elements.
    """


class CommentReply(BaseModel):
    """Record of a single reply added to an existing comment thread.

    The comment_id is the Com:N ID of the comment being replied to.
    The reply_text is the plain text content of the reply.
    """

    comment_id: str
    reply_text: str


class ReplyResult(BaseModel):
    """Structured result of a reply_to_comments operation.

    Contains the list of all successfully added replies. Returned
    only when all requested replies have been added and saved.
    """

    replies: list[CommentReply]
    validation_warnings: list[str] = []


class AddedComment(BaseModel):
    """Record of a single new standalone comment added to the document.

    The anchor_id identifies what the comment is attached to (Chg:N
    for tracked changes, or text string for text-match anchoring).
    The comment_text is the plain text content of the comment.
    The comment_id is the assigned Com:N ID for the new comment.
    """

    anchor_id: str
    comment_text: str
    comment_id: str


class FailedComment(BaseModel):
    """Record of a comment that failed to attach during add_comments.

    Captures the anchor and reason so the caller can report which
    comments were skipped without aborting the entire batch.
    """

    anchor_id: str
    comment_text: str
    reason: str


class AddCommentResult(BaseModel):
    """Structured result of an add_comments operation.

    Contains successfully added comments and any that failed to attach.
    Partial success is normal when some anchors become invalid (e.g.
    after an accept removes tracked change markup).
    """

    added_comments: list[AddedComment]
    failed_comments: list[FailedComment] = []
    validation_warnings: list[str] = []


class ResolvedThread(BaseModel):
    """Record of a single resolved comment thread.

    The comment_id is the Com:N ID that was requested for resolution.
    The root_comment_id is the actual root Com:N of the thread that
    was marked as resolved (may differ if a reply ID was provided).
    """

    comment_id: str
    root_comment_id: str


class ResolveResult(BaseModel):
    """Structured result of a resolve_comments operation.

    Contains the list of all successfully resolved threads. Returned
    only when all requested threads have been resolved and saved.
    """

    resolved_threads: list[ResolvedThread]
    validation_warnings: list[str] = []
