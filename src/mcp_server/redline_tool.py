"""MCP tool for first-pass redlining on clean documents.

Provides the redline_document tool which applies tracked changes to a clean
.docx file. Claude builds the edit list based on its analysis of the document
and the user's instructions, then calls this tool to create native OOXML
tracked changes attributed to the specified author.

This tool is mode-agnostic -- it works with any edit list regardless of how
Claude built it. Comments pass through as-is: None means no comment, text
means exact text attached. Commenting judgment lives in SKILL.md prompting,
not in the tool.
"""

from adeu import DocumentEdit
from mcp.types import ToolAnnotations

from src.mcp_server import mcp
from src.mcp_server.error_sanitizer import sanitize_error_message
from src.models.author_config import AuthorConfig
from src.pipeline.first_pass import run_first_pass_pipeline


@mcp.tool(
    annotations=ToolAnnotations(
        title="Redline Document",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def redline_document(
    input_path: str,
    output_path: str,
    edits: list[dict[str, str | None]],
    author_name: str,
) -> str:
    """Apply tracked changes to a clean document.

    Takes a list of edit specifications and creates native OOXML tracked
    changes (w:ins, w:del) attributed to the specified author. Each edit
    targets existing text and specifies a replacement, deletion, or
    insertion with an optional comment.

    Each edit dict has:
      - target_text: The exact text to find in the document.
      - new_text: Replacement text ("" for pure deletion; None is
        also accepted and coerced to "" for backward compatibility).
      - comment: Optional rationale text attached as a Word comment,
        or None for no comment.

    For pure insertion, set target_text to the anchor text and new_text
    to the anchor text plus the inserted text.

    This tool does NOT interpret instructions -- Claude builds the edit
    list based on its own analysis of the document and instructions.

    Args:
        input_path: Absolute path to the input .docx document.
        output_path: Absolute path for the output .docx document.
        edits: List of edit dicts matching DocumentEdit shape.
        author_name: Client author name for Track Changes attribution.

    Returns:
        JSON string with output_path, applied edits, skipped edits,
        and validation warnings. On failure, returns an error string.
    """
    try:
        for edit_dict in edits:
            if edit_dict.get("new_text") is None:
                edit_dict["new_text"] = ""
        edit_models = [DocumentEdit(**e) for e in edits]
        config = AuthorConfig(name=author_name)
        result = run_first_pass_pipeline(
            input_path=input_path,
            output_path=output_path,
            edits=edit_models,
            author_config=config,
        )
        return result.model_dump_json(indent=2)
    except Exception as error:
        return f"Error redlining document: {sanitize_error_message(error)}"
