"""MCP tools for Styler formatting extraction and splicing.

Provides two thin MCP wrappers around the existing deterministic
styler_extraction functions, so Claude can perform the formatting
cleanup step described in SKILL.md via explicit MCP tool calls.

Usage:
    extract_styler_triplets → get raw OOXML triplets for inspection
    splice_styler_fragments → splice corrected fragments back in
"""

import json

from mcp.types import ToolAnnotations

from src.mcp_server import mcp
from src.mcp_server.error_sanitizer import sanitize_error_message
from src.pipeline.styler import OoxmlFragment
from src.pipeline.styler_extraction import (
    extract_client_triplets,
    splice_corrected_fragments,
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Extract Styler Triplets",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def extract_styler_triplets(
    document_path: str,
    client_author: str,
) -> str:
    """Extract client-authored paragraphs with surrounding context as OOXML.

    Finds every paragraph containing a client-authored tracked change
    (w:ins or w:del) and returns it with its above/below neighbours as
    raw OOXML strings. Use this to inspect formatting before splicing.

    Args:
        document_path: Absolute path to the .docx document.
        client_author: Author name to match against w:author attributes.

    Returns:
        JSON list of triplet objects with paragraph_above,
        target_paragraph, paragraph_below, and paragraph_index.
    """
    try:
        triplets = extract_client_triplets(document_path, client_author)
        return json.dumps(
            [t.model_dump() for t in triplets], indent=2,
        )
    except Exception as error:
        return f"Error extracting triplets: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Splice Styler Fragments",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
def splice_styler_fragments(
    document_path: str,
    fragments: list[dict[str, str | int]],
) -> str:
    """Splice corrected OOXML fragments back into the document.

    Replaces paragraphs at the specified indices with corrected XML.
    Processes in reverse index order to avoid position drift. The
    document is saved in-place.

    Each fragment dict must have:
      - paragraph_index: integer position in the document body
      - corrected_xml: the corrected raw OOXML string

    Args:
        document_path: Absolute path to the .docx document to modify.
        fragments: List of fragment dicts to splice in.

    Returns:
        JSON object with fragments_spliced count on success.
    """
    try:
        parsed = [OoxmlFragment(**f) for f in fragments]
        splice_corrected_fragments(document_path, document_path, parsed)
        return json.dumps({
            "status": "success",
            "fragments_spliced": len(parsed),
        })
    except Exception as error:
        return f"Error splicing fragments: {sanitize_error_message(error)}"
