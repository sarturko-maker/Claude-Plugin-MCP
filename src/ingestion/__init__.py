"""Document ingestion package for the agentic negotiation plugin.

Provides functions to extract text from .docx documents in different
views (clean accepted-all, annotated with CriticMarkup) and to extract
structured author metadata from tracked changes. This package wraps
Adeu's extraction capabilities with validation and error handling.

Public API:
    extract_clean_text: Extract accepted-all view text from a .docx file.
    extract_annotated_text: Extract CriticMarkup-annotated text from a .docx file.
    extract_authors: Extract unique authors and change statistics from a .docx file.
    build_state_of_play: Build flat per-change state of play from a .docx file.
    IngestionError: Single error type for all ingestion failures.
"""

from src.ingestion.annotated_extractor import extract_annotated_text
from src.ingestion.author_extractor import extract_authors
from src.ingestion.clean_extractor import extract_clean_text
from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import IngestionError

__all__ = [
    "extract_clean_text",
    "extract_annotated_text",
    "extract_authors",
    "build_state_of_play",
    "IngestionError",
]
