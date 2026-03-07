"""Tracked change entry and state of play models.

Defines Pydantic models for individual tracked changes and the
overall negotiation state. TrackedChangeEntry captures a single
pending change with its metadata. StateOfPlay aggregates all
authors and changes for the entire document.

These models are consumed by downstream phases for accept/reject
decisions and counter-proposal generation.
"""

from typing import Literal

from pydantic import BaseModel, computed_field

from src.models.party import AuthorInfo


class TrackedChangeEntry(BaseModel):
    """A single pending tracked change in the document.

    Each entry represents one insertion, deletion, or comment that
    has not yet been accepted. The change_id uses the convention
    Chg:N for tracked changes and Com:N for comments. The party_role
    field defaults to 'unknown' and is populated by Claude after
    role assignment.
    """

    change_id: str
    change_type: Literal["insertion", "deletion", "comment"]
    author: str
    date: str
    party_role: str = "unknown"
    paragraph_context: str
    changed_text: str
    ooxml_id: str = ""
    replies: list["TrackedChangeEntry"] = []


class StateOfPlay(BaseModel):
    """Complete negotiation state of a document.

    Combines the author summary with a flat list of all pending
    tracked changes. The pending_count property returns the total
    number of unresolved changes.
    """

    authors: list[AuthorInfo]
    changes: list[TrackedChangeEntry]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pending_count(self) -> int:
        """Number of pending tracked changes in the document."""
        return len(self.changes)
