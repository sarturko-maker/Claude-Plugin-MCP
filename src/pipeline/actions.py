"""Typed action models for the negotiation pipeline.

Each action represents a single instruction the user gives to the pipeline:
accept a change, counter-propose replacement text, add a comment, reply to
a comment, or resolve a comment thread. Pydantic validators enforce ID
prefix conventions (Chg: for tracked changes, Com: for comments).

NegotiationAction is a discriminated union of all action types, used as the
pipeline's input format. sort_actions_by_execution_order ensures actions
execute in the correct sequence: accepts before counter-proposals before
comments before replies before resolves.
"""

from typing import Literal, Union

from pydantic import BaseModel, field_validator


EXECUTION_ORDER: dict[str, int] = {
    "accept": 0,
    "counter_propose": 1,
    "add_comment": 2,
    "reply": 3,
    "resolve": 4,
}


class AcceptAction(BaseModel):
    """Accept a tracked change, removing its markup from the document.

    Attributes:
        action_type: Always "accept".
        change_id: Tracked change identifier (must start with "Chg:").
    """

    action_type: Literal["accept"] = "accept"
    change_id: str

    @field_validator("change_id")
    @classmethod
    def validate_change_id_prefix(cls, value: str) -> str:
        """Enforce that change_id starts with 'Chg:' prefix."""
        if not value.startswith("Chg:"):
            raise ValueError("change_id must start with 'Chg:'")
        return value


class CounterProposeAction(BaseModel):
    """Counter-propose replacement text for a tracked change.

    Layers a client-attributed deletion of the counterparty's text
    plus a client-attributed insertion of the replacement text.

    Attributes:
        action_type: Always "counter_propose".
        change_id: Tracked change identifier (must start with "Chg:").
        replacement_text: Text to propose instead of the counterparty's change.
    """

    action_type: Literal["counter_propose"] = "counter_propose"
    change_id: str
    replacement_text: str

    @field_validator("change_id")
    @classmethod
    def validate_change_id_prefix(cls, value: str) -> str:
        """Enforce that change_id starts with 'Chg:' prefix."""
        if not value.startswith("Chg:"):
            raise ValueError("change_id must start with 'Chg:'")
        return value

    @field_validator("replacement_text")
    @classmethod
    def validate_replacement_text_not_empty(cls, value: str) -> str:
        """Enforce that replacement_text is non-empty for counter-proposals."""
        if not value.strip():
            raise ValueError(
                "counter_propose requires non-empty replacement_text"
            )
        return value


class AddCommentAction(BaseModel):
    """Add a standalone comment anchored to a change or text.

    Attributes:
        action_type: Always "add_comment".
        anchor_id: Anchor for the comment -- either a change ID (Chg:N)
            or a text string to locate in the document.
        comment_text: Text content of the comment.
    """

    action_type: Literal["add_comment"] = "add_comment"
    anchor_id: str
    comment_text: str


class ReplyAction(BaseModel):
    """Reply to an existing comment thread.

    Attributes:
        action_type: Always "reply".
        comment_id: Comment identifier (must start with "Com:").
        reply_text: Text content of the reply.
    """

    action_type: Literal["reply"] = "reply"
    comment_id: str
    reply_text: str

    @field_validator("comment_id")
    @classmethod
    def validate_comment_id_prefix(cls, value: str) -> str:
        """Enforce that comment_id starts with 'Com:' prefix."""
        if not value.startswith("Com:"):
            raise ValueError("comment_id must start with 'Com:'")
        return value


class ResolveAction(BaseModel):
    """Resolve (mark as done) a comment thread.

    Attributes:
        action_type: Always "resolve".
        comment_id: Comment identifier (must start with "Com:").
    """

    action_type: Literal["resolve"] = "resolve"
    comment_id: str

    @field_validator("comment_id")
    @classmethod
    def validate_comment_id_prefix(cls, value: str) -> str:
        """Enforce that comment_id starts with 'Com:' prefix."""
        if not value.startswith("Com:"):
            raise ValueError("comment_id must start with 'Com:'")
        return value


NegotiationAction = Union[
    AcceptAction,
    CounterProposeAction,
    AddCommentAction,
    ReplyAction,
    ResolveAction,
]


def sort_actions_by_execution_order(
    actions: list[NegotiationAction],
) -> list[NegotiationAction]:
    """Sort actions into correct execution order.

    Order: accepts -> counter-proposals -> add_comments -> replies -> resolves.
    This ensures accepts remove markup before counter-proposals target the same
    regions, and comments execute after all text edits are complete.
    """
    return sorted(
        actions, key=lambda action: EXECUTION_ORDER[action.action_type]
    )
