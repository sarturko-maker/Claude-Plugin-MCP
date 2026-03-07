"""MCP tools for individual negotiation actions.

Provides tools for each atomic negotiation operation:
- accept_changes: Accept counterparty tracked changes.
- counter_propose_changes: Layer client counter-proposals.
- add_comments: Add standalone comments to the document.
- reply_to_comments: Reply to existing comment threads.
- resolve_comments: Mark comment threads as resolved.

Each tool wraps the corresponding src.negotiation function, converting
MCP-friendly parameters to the internal Pydantic models.
"""

from mcp.types import ToolAnnotations

from src.models.author_config import AuthorConfig
from src.mcp_server import mcp
from src.mcp_server.error_sanitizer import sanitize_error_message
from src.negotiation.accept_changes import accept_changes as _accept
from src.negotiation.add_comments import add_comments as _add_comments
from src.negotiation.counter_propose_changes import (
    counter_propose_changes as _counter_propose,
)
from src.negotiation.reply_to_comments import (
    reply_to_comments as _reply,
)
from src.negotiation.resolve_comments import (
    resolve_comments as _resolve,
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Accept Changes",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def accept_changes(
    input_path: str, output_path: str, change_ids: list[str]
) -> str:
    """Accept tracked changes by their Chg:N IDs.

    Removes the tracked change markup for each ID, committing the
    text to the clean document. The counterparty's change becomes
    accepted. Only accepts tracked changes (Chg:N), not comments.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        change_ids: List of Chg:N IDs to accept (e.g. ["Chg:1", "Chg:3"]).
    """
    try:
        result = _accept(input_path, output_path, change_ids)
        response = result.model_dump_json(indent=2)
        return (
            response + "\n\nWARNING: Chg:N IDs have been renumbered in "
            "the output file. For subsequent operations (add_comments, "
            "counter_propose), use ooxml:NNN anchors from the original "
            "get_state_of_play output, or re-read state of play on the "
            "output file to get updated Chg:N IDs."
        )
    except Exception as error:
        return f"Error accepting changes: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Counter-Propose Changes",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def counter_propose_changes(
    input_path: str,
    output_path: str,
    proposals: list[dict[str, str]],
    author_name: str,
) -> str:
    """Counter-propose tracked changes with client replacement text.

    Layers client-attributed redlines on top of the counterparty's
    markup. Each proposal targets a Chg:N ID and provides replacement
    text. The counterparty's change stays visible; the client's
    deletion and insertion are layered on top.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        proposals: List of dicts with "change_id" and "replacement_text".
        author_name: Client author name for Track Changes attribution.
    """
    try:
        tuples = [
            (p["change_id"], p["replacement_text"]) for p in proposals
        ]
        config = AuthorConfig(name=author_name)
        result = _counter_propose(input_path, output_path, tuples, config)
        response = result.model_dump_json(indent=2)
        return (
            response + "\n\nWARNING: Chg:N IDs have been renumbered in "
            "the output file. For subsequent operations (add_comments), "
            "use ooxml:NNN anchors from the original get_state_of_play "
            "output, or re-read state of play on the output file to get "
            "updated Chg:N IDs."
        )
    except Exception as error:
        return f"Error counter-proposing changes: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Add Comments",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def add_comments(
    input_path: str,
    output_path: str,
    comments: list[dict[str, str]],
    author_name: str,
) -> str:
    """Add standalone comments to the document.

    Each comment is anchored by one of three modes:
    - Chg:N ID: anchors to a tracked change (fragile -- IDs renumber
      after accept or counter-propose operations)
    - ooxml:NNN: anchors to a tracked change by its stable OOXML w:id
      (PREFERRED when chaining operations -- use the ooxml_id from
      get_state_of_play, which does not change between steps)
    - Text string: anchors by finding exact text in a paragraph

    IMPORTANT: After accept_changes or counter_propose_changes, Chg:N
    IDs are renumbered. Use ooxml:NNN anchors (from the ooxml_id field
    in get_state_of_play output) to avoid comments landing on the
    wrong clause.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        comments: List of dicts with "anchor_id" and "comment_text".
        author_name: Client author name for comment attribution.
    """
    try:
        tuples = [
            (c["anchor_id"], c["comment_text"]) for c in comments
        ]
        config = AuthorConfig(name=author_name)
        result = _add_comments(input_path, output_path, tuples, config)
        return result.model_dump_json(indent=2)
    except Exception as error:
        return f"Error adding comments: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Reply to Comments",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def reply_to_comments(
    input_path: str,
    output_path: str,
    replies: list[dict[str, str]],
    author_name: str,
) -> str:
    """Reply to existing comment threads.

    Adds threaded replies to counterparty comments. Replies appear
    nested under the parent comment in Word's review pane.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        replies: List of dicts with "comment_id" and "reply_text".
        author_name: Client author name for reply attribution.
    """
    try:
        tuples = [
            (r["comment_id"], r["reply_text"]) for r in replies
        ]
        config = AuthorConfig(name=author_name)
        result = _reply(input_path, output_path, tuples, config)
        return result.model_dump_json(indent=2)
    except Exception as error:
        return f"Error replying to comments: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Resolve Comments",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def resolve_comments(
    input_path: str, output_path: str, comment_ids: list[str]
) -> str:
    """Resolve comment threads by marking them as done.

    Sets w15:done='1' on the root comment in each thread. If a reply
    ID is provided, traces up to the root before resolving.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        comment_ids: List of Com:N IDs to resolve.
    """
    try:
        result = _resolve(input_path, output_path, comment_ids)
        return result.model_dump_json(indent=2)
    except Exception as error:
        return f"Error resolving comments: {sanitize_error_message(error)}"
