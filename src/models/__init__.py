"""Pydantic data models for the agentic negotiation plugin.

Provides typed data contracts for party identification, tracked change
entries, document state, accept-changes results, counter-proposal
results, comment operation results, author configuration, and batch
edit results. These models are used by ingestion and negotiation modules
to return structured data and by downstream phases to consume it.

Public API:
    AuthorConfig: Client author configuration for tracked change attribution.
    AuthorInfo: Summary of a single author found in tracked changes.
    AuthorSummary: All authors found with change statistics.
    BatchEditResult: Result of applying multiple edits with skip-on-failure.
    EditFailure: Record of a single edit that failed to apply.
    TrackedChangeEntry: A single pending tracked change in the document.
    StateOfPlay: Complete negotiation state of a document.
    AcceptError: Error type for accept-changes failures.
    AcceptedChange: Record of a single accepted tracked change.
    AcceptResult: Structured result of an accept_changes operation.
    CounterProposalError: Error type for counter-proposal failures.
    CounterProposedChange: Record of a single counter-proposal applied.
    CounterProposalResult: Structured result of a counter_propose_changes operation.
    CommentError: Error type for comment operation failures.
    CommentReply: Record of a single reply to an existing comment.
    ReplyResult: Structured result of a reply_to_comments operation.
    AddedComment: Record of a single new standalone comment.
    AddCommentResult: Structured result of an add_comments operation.
    ResolvedThread: Record of a single resolved comment thread.
    ResolveResult: Structured result of a resolve_comments operation.
"""

from src.models.accept import AcceptedChange, AcceptError, AcceptResult
from src.models.author_config import AuthorConfig
from src.models.change import StateOfPlay, TrackedChangeEntry
from src.models.comment import (
    AddCommentResult,
    AddedComment,
    CommentError,
    CommentReply,
    ReplyResult,
    ResolvedThread,
    ResolveResult,
)
from src.models.counter_proposal import (
    CounterProposalError,
    CounterProposalResult,
    CounterProposedChange,
)
from src.models.edit_result import BatchEditResult, EditFailure
from src.models.party import AuthorInfo, AuthorSummary

__all__ = [
    "AcceptedChange",
    "AcceptError",
    "AcceptResult",
    "AddCommentResult",
    "AddedComment",
    "AuthorConfig",
    "AuthorInfo",
    "AuthorSummary",
    "BatchEditResult",
    "CommentError",
    "CommentReply",
    "CounterProposalError",
    "CounterProposalResult",
    "CounterProposedChange",
    "EditFailure",
    "ReplyResult",
    "ResolvedThread",
    "ResolveResult",
    "TrackedChangeEntry",
    "StateOfPlay",
]
