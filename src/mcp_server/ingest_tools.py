"""MCP tools for document ingestion and state-of-play extraction.

Provides three tools:
- ingest_document: Returns both clean and annotated text views.
- build_state_of_play: Returns the full negotiation state as JSON.

These are read-only operations that do not modify the document.
"""

from mcp.types import ToolAnnotations

from src.ingestion.annotated_extractor import extract_annotated_text
from src.ingestion.clean_extractor import extract_clean_text
from src.ingestion.state_of_play import build_state_of_play as _build_sop
from src.mcp_server import mcp
from src.mcp_server.error_sanitizer import sanitize_error_message


@mcp.tool(
    annotations=ToolAnnotations(
        title="Ingest Document",
        readOnlyHint=True,
        openWorldHint=False,
    )
)
def ingest_document(file_path: str) -> str:
    """Ingest a .docx document and return both text views.

    Returns the clean text (all changes accepted) and the annotated
    CriticMarkup text (tracked changes with author attribution) as
    a combined string. Use this to read a document before deciding
    how to respond.

    Args:
        file_path: Absolute path to the .docx file.
    """
    try:
        clean = extract_clean_text(file_path)
        annotated = extract_annotated_text(file_path)
        return (
            "=== CLEAN TEXT (all changes accepted) ===\n"
            f"{clean}\n\n"
            "=== ANNOTATED TEXT (tracked changes with attribution) ===\n"
            f"{annotated}"
        )
    except Exception as error:
        return f"Error ingesting document: {sanitize_error_message(error)}"


@mcp.tool(
    annotations=ToolAnnotations(
        title="Get State of Play",
        readOnlyHint=True,
        openWorldHint=False,
    )
)
def get_state_of_play(file_path: str) -> str:
    """Build the complete state of play from a .docx document.

    Returns a JSON object listing every pending tracked change and
    comment with sequential Chg:N and Com:N IDs, author, date,
    paragraph context, and changed text. Also includes the author
    summary for party identification.

    Args:
        file_path: Absolute path to the .docx file.
    """
    try:
        state = _build_sop(file_path)
        return state.model_dump_json(indent=2)
    except Exception as error:
        return f"Error building state of play: {sanitize_error_message(error)}"
