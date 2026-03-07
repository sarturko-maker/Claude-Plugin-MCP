"""Negotiation decision models for Claude's per-change analysis output.

NegotiationDecision captures Claude's decision for a single tracked change:
what action to take, optional replacement text or comment, and reasoning.
DecisionDetail and DecisionSummary support supervised mode where the user
reviews decisions before execution. NegotiationResult wraps the pipeline
result with the full decision context for audit trail.
"""

from typing import Literal

from pydantic import BaseModel, field_validator

from src.config.models import NegotiationConfig
from src.pipeline.results import PipelineResult


class NegotiationDecision(BaseModel):
    """Claude's decision for a single tracked change or comment.

    Attributes:
        change_id: Tracked change or comment identifier (Chg:N or Com:N).
        action: What to do with this change.
        replacement_text: Proposed replacement for counter_propose actions.
        comment_text: Text for comment, reply, or accept acknowledgement.
        reasoning: Brief explanation of why this decision was made.
    """

    change_id: str
    action: Literal[
        "accept",
        "counter_propose",
        "comment",
        "reply",
        "resolve",
        "no_action",
    ]
    replacement_text: str = ""
    comment_text: str = ""
    reasoning: str = ""

    @field_validator("change_id")
    @classmethod
    def validate_change_id_prefix(cls, value: str) -> str:
        """Enforce that change_id starts with 'Chg:' or 'Com:' prefix."""
        if not value.startswith(("Chg:", "Com:")):
            raise ValueError(
                "change_id must start with 'Chg:' or 'Com:' prefix"
            )
        return value


class DecisionDetail(BaseModel):
    """Single decision detail for supervised mode preview.

    Attributes:
        change_id: Tracked change or comment identifier.
        change_summary: Brief description from state of play.
        action: Action type as a string.
        reasoning: Why this decision was made.
        replacement_text: Proposed replacement text (counter_propose only).
        comment_text: Comment or reply text.
    """

    change_id: str
    change_summary: str
    action: str
    reasoning: str = ""
    replacement_text: str = ""
    comment_text: str = ""


class DecisionSummary(BaseModel):
    """Supervised mode preview grouping decisions by action type.

    Provides a to_prompt() method that formats the summary as a
    human-readable string for user review before execution.

    Attributes:
        total_changes: Total number of changes in the document.
        accepts: Decisions to accept changes.
        counter_proposals: Decisions to counter-propose.
        comments: Decisions to add standalone comments.
        replies: Decisions to reply to comment threads.
        resolves: Decisions to resolve comment threads.
        no_actions: Decisions to take no action.
    """

    total_changes: int
    accepts: list[DecisionDetail] = []
    counter_proposals: list[DecisionDetail] = []
    comments: list[DecisionDetail] = []
    replies: list[DecisionDetail] = []
    resolves: list[DecisionDetail] = []
    no_actions: list[DecisionDetail] = []

    def to_prompt(self) -> str:
        """Format the decision summary as a human-readable string.

        Groups decisions by action type with headers and details.
        Omits sections with no decisions. Returns a multi-line
        string suitable for display to the user.
        """
        lines: list[str] = []
        lines.append(f"Decision Summary ({self.total_changes} changes)")
        lines.append("=" * 50)

        sections = [
            ("Accepts", self.accepts),
            ("Counter-Proposals", self.counter_proposals),
            ("Comments", self.comments),
            ("Replies", self.replies),
            ("Resolves", self.resolves),
            ("No Action", self.no_actions),
        ]

        for header, details in sections:
            if not details:
                continue
            lines.append("")
            lines.append(f"## {header} ({len(details)})")
            for detail in details:
                lines.append(f"  - {detail.change_id}: {detail.change_summary}")
                if detail.reasoning:
                    lines.append(f"    Reason: {detail.reasoning}")
                if detail.replacement_text:
                    lines.append(f"    Replace: {detail.replacement_text}")
                if detail.comment_text:
                    lines.append(f"    Comment: {detail.comment_text}")

        return "\n".join(lines)


class NegotiationResult(BaseModel):
    """Complete result of a negotiation pipeline execution.

    Wraps the raw pipeline result with the full set of decisions
    and a grouped summary for audit trail and reporting. Optionally
    includes the NegotiationConfig used, for audit trail purposes.

    Attributes:
        pipeline_result: Raw pipeline execution result.
        decisions: List of all negotiation decisions made.
        summary: Grouped summary of decisions by action type.
        config: The NegotiationConfig used for this negotiation, if provided.
    """

    pipeline_result: PipelineResult
    decisions: list[NegotiationDecision]
    summary: DecisionSummary
    config: NegotiationConfig | None = None
