"""Error message sanitizer for MCP tool responses.

Strips absolute file paths from exception messages before they reach
the MCP client. Python exceptions from lxml, python-docx, and adeu
may include full filesystem paths in their string representation.
Leaking these paths would expose server directory structure.

Usage:
    from src.mcp_server.error_sanitizer import sanitize_error_message

    except Exception as error:
        return f"Error doing thing: {sanitize_error_message(error)}"
"""

import re


_PATH_PATTERN = re.compile(r"(?<![a-zA-Z0-9_\-.])(/(?:[a-zA-Z0-9_\-.])+(?:/[^\s:'\",\)]+)+)")
"""Matches absolute Unix paths with at least two components (e.g.
/home/user/file.docx). Requires the leading / to NOT follow a word
character, so relative paths like src/models/file.py are ignored.
Each match is replaced with just the final filename component."""


def sanitize_error_message(error: Exception) -> str:
    """Convert an exception to a string with absolute paths removed.

    Replaces every absolute path (e.g. /home/user/docs/file.docx) with
    just the filename portion (e.g. file.docx). Preserves the rest of
    the error message unchanged.

    Args:
        error: The caught exception.

    Returns:
        Sanitized error string safe for MCP client display.
    """
    message = str(error)
    return _strip_absolute_paths(message)


def _strip_absolute_paths(text: str) -> str:
    """Replace absolute paths in text with their filename-only portion.

    Args:
        text: Raw error message that may contain absolute paths.

    Returns:
        Text with all absolute paths replaced by filenames.
    """

    def _replace_with_filename(match: re.Match[str]) -> str:
        """Extract the filename from a matched absolute path."""
        path = match.group(1)
        # Extract the last component (filename) from the path
        parts = path.rstrip("/").rsplit("/", 1)
        return parts[-1] if len(parts) > 1 else path

    return _PATH_PATTERN.sub(_replace_with_filename, text)
