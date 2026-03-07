"""Negotiation operations package for the agentic negotiation plugin.

Provides functions to mutate tracked changes in .docx documents as part
of the contract negotiation workflow. Operations include accepting changes,
counter-proposing, and managing comments (reply, add, resolve).

Public API:
    accept_changes: Accept tracked changes by Chg:N ID.
    AcceptError: Error type for accept-changes failures.
    counter_propose_changes: Counter-propose tracked changes with client redlines.
    CounterProposalError: Error type for counter-proposal failures.
    reply_to_comments: Add threaded replies to existing comments.
    add_comments: Add new standalone comments anchored to changes or text.
    resolve_comments: Mark comment threads as resolved.
    CommentError: Error type for comment operation failures.
"""

from src.models.accept import AcceptError
from src.models.author_config import AuthorConfig
from src.models.comment import CommentError
from src.models.counter_proposal import CounterProposalError
from src.negotiation.accept_changes import accept_changes
from src.negotiation.add_comments import add_comments
from src.negotiation.counter_propose_changes import counter_propose_changes
from src.negotiation.reply_to_comments import reply_to_comments
from src.negotiation.resolve_comments import resolve_comments

__all__ = [
    "accept_changes",
    "AcceptError",
    "add_comments",
    "AuthorConfig",
    "CommentError",
    "counter_propose_changes",
    "CounterProposalError",
    "reply_to_comments",
    "resolve_comments",
]
