"""MCP tool for full pipeline execution.

Provides the execute_pipeline tool which runs the complete negotiation
pipeline: validate decisions, convert to actions, execute via temp-file
chaining, optional Styler pass, and output validation.

This is the high-level "do everything" tool. For granular control,
use the individual action tools in action_tools.py.
"""

from mcp.types import ToolAnnotations

from src.mcp_server import mcp
from src.mcp_server.error_sanitizer import sanitize_error_message
from src.models.author_config import AuthorConfig
from src.orchestration.decision import NegotiationDecision
from src.orchestration.negotiator import negotiate


@mcp.tool(
    annotations=ToolAnnotations(
        title="Execute Pipeline",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def execute_pipeline(
    input_path: str,
    output_path: str,
    decisions: list[dict[str, str]],
    author_name: str,
) -> str:
    """Execute the full negotiation pipeline with a list of decisions.

    Takes Claude's per-change decisions (accept, counter_propose,
    comment, reply, resolve, no_action) and executes them all in the
    correct order: accepts first, then counter-proposals, then
    comments, then replies, then resolves.

    IMPORTANT -- Choose the right approach for each change:
    1. counter_propose: disagree with the substance, layer your redline
       over theirs. More common in early rounds.
    2. accept + fresh edits + comment: substantially agree but want
       to tweak specific words. Signals convergence in later rounds.
       Always comment that you accepted with amendments.
    3. pure accept + comment: fully agree, comment "Accepted".
    Calibrate to negotiation stage: counter freely early, bias toward
    acceptance late. Don't counter just because you'd word it
    differently -- only counter when the substance is wrong.

    Each decision dict must have:
      - change_id: "Chg:N" or "Com:N"
      - action: one of "accept", "counter_propose", "comment",
                "reply", "resolve", "no_action"
      - replacement_text: (optional) for counter_propose
      - comment_text: (optional) for comment/reply
      - reasoning: (optional) explanation

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        decisions: List of decision dicts.
        author_name: Client author name for Track Changes attribution.
    """
    try:
        parsed = [NegotiationDecision(**d) for d in decisions]
        config = AuthorConfig(name=author_name)
        result = negotiate(
            input_path=input_path,
            output_path=output_path,
            decisions=parsed,
            author_config=config,
        )
        return result.model_dump_json(indent=2)
    except Exception as error:
        return f"Error executing pipeline: {sanitize_error_message(error)}"
