"""Clean text extraction from .docx documents via Adeu.

Extracts the accepted-all view (clean text) from a Word document,
resolving all tracked changes to their final state. Uses Adeu's
extract_text_from_stream as the underlying extraction engine.
"""

import io

from adeu import extract_text_from_stream

from src.ingestion.validation import IngestionError, validate_docx_path


def extract_clean_text(file_path: str) -> str:
    """Extract accepted-all view text from a .docx document.

    Validates the file path, reads the document into a BytesIO stream,
    and delegates to Adeu for clean text extraction. All tracked changes
    are resolved to their accepted state.

    Args:
        file_path: String path to the .docx file.

    Returns:
        Plain text string representing the accepted-all view of the document.

    Raises:
        IngestionError: If the file is invalid or extraction fails.
    """
    validated_path = validate_docx_path(file_path)

    try:
        with open(validated_path, "rb") as file_handle:
            stream = io.BytesIO(file_handle.read())
        return extract_text_from_stream(
            stream, filename=validated_path.name, clean_view=True,
        )
    except IngestionError:
        raise
    except Exception as error:
        raise IngestionError(
            f"Failed to extract text from {validated_path.name}: {error}"
        ) from error
