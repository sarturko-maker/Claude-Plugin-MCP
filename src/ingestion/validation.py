"""File path validation and error types for document ingestion.

Provides validate_docx_path() to check that a given path is a valid,
existing .docx file before any extraction work begins. Defines
IngestionError as the single error type for all ingestion failures.
"""

from pathlib import Path


class IngestionError(Exception):
    """Raised when document ingestion fails.

    Wraps all ingestion-related errors with a descriptive, LLM-readable
    message. No class hierarchy -- a single type with a clear message string.
    """


def validate_docx_path(file_path: str) -> Path:
    """Validate that a file path points to an existing .docx file.

    Converts the string to a Path, resolves it to absolute, then checks:
    1. No path traversal components (..) in resolved path parts.
    2. File exists on disk.
    3. File extension is .docx (case-insensitive).

    Args:
        file_path: String path to the document file.

    Returns:
        Resolved absolute Path to the validated file.

    Raises:
        IngestionError: If the path is invalid, the file is missing,
            or the extension is not .docx.
    """
    path = Path(file_path).resolve()

    # Check for path traversal: reject if '..' appears in any component
    # of the original (unresolved) path. This catches attempts to escape
    # the intended directory even when resolve() normalizes them away.
    raw_parts = Path(file_path).parts
    if ".." in raw_parts:
        raise IngestionError("Invalid file path")

    if not path.exists():
        raise IngestionError(f"File not found: {path.name}")

    if path.suffix.lower() != ".docx":
        raise IngestionError(f"Not a .docx file: {path.name}")

    return path
