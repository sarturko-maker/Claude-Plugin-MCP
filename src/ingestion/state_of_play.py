# TODO: reduce state_of_play output size — currently too verbose for
# multi-round negotiations. Target <3k tokens. See token-optimization-roadmap.md.
"""State-of-play builder for tracked changes in .docx documents.

Produces a flat list of all pending tracked changes with sequential
Chg:N and Com:N IDs, including type, author, date, paragraph context,
and changed text. Downstream phases (accept, counter-propose, comment)
consume this list to act on individual changes by ID.

Uses the OOXML walking pattern established in Phase 3, with author
extraction logic from Phase 4 Plan 01. Element processing helpers
are in state_of_play_helpers.py to stay under the 200-line limit.
"""

from docx import Document
from docx.oxml.ns import qn

from adeu.utils.docx import (
    get_paragraph_prefix,
    get_run_text,
    get_visible_runs,
    iter_document_parts,
)

from src.ingestion.annotated_helpers import extract_del_text
from src.ingestion.author_extractor import extract_authors_from_document
from src.ingestion.comment_loader import load_comments, load_comments_extended
from src.ingestion.reply_attachment import attach_reply_comments
from src.ingestion.sdt_unwrapper import iter_effective_children
from src.ingestion.state_of_play_helpers import (
    make_deletion_entry,
    process_comment_ref,
    process_insertion,
)
from src.ingestion.validation import validate_docx_path
from src.models.change import StateOfPlay, TrackedChangeEntry


def build_state_of_play(file_path: str) -> StateOfPlay:
    """Build the complete negotiation state of play from a .docx document.

    Walks all document parts, extracts every pending tracked change and
    comment as a TrackedChangeEntry with a sequential Chg:N or Com:N ID.
    Also extracts the author summary. Returns a StateOfPlay combining both.

    Args:
        file_path: String path to the .docx document.

    Returns:
        StateOfPlay with authors list and flat changes list.

    Raises:
        IngestionError: If the file path is invalid or not a .docx file.
    """
    validated_path = validate_docx_path(file_path)
    document = Document(str(validated_path))

    author_summary = extract_authors_from_document(document)
    comments_lookup = load_comments(document)
    extended_lookup = load_comments_extended(document)

    entries, comment_counter = _walk_document_for_changes(
        document, comments_lookup
    )
    attach_reply_comments(
        entries, comments_lookup, extended_lookup, comment_counter
    )
    return StateOfPlay(authors=author_summary.authors, changes=entries)


def _walk_document_for_changes(
    document: Document, comments_lookup: dict[str, dict]
) -> tuple[list[TrackedChangeEntry], int]:
    """Walk all document parts and collect tracked change entries.

    Iterates paragraphs in document order. For each paragraph, checks
    child elements for w:ins, w:del, and w:r with comment references.
    Returns entries in document order with sequential IDs, plus the
    final comment counter for reply attachment.

    Args:
        document: A python-docx Document object.
        comments_lookup: Comment ID to metadata dict from load_comments.

    Returns:
        Tuple of (entries list, final comment_counter).
    """
    entries: list[TrackedChangeEntry] = []
    change_counter = 0
    comment_counter = 0

    for part in iter_document_parts(document):
        for paragraph in part.paragraphs:
            context = _get_paragraph_context(paragraph)

            for child in iter_effective_children(paragraph._element):
                if child.tag == qn("w:ins"):
                    change_counter, comment_counter = process_insertion(
                        child, context, comments_lookup, entries,
                        change_counter, comment_counter,
                    )
                elif child.tag == qn("w:del"):
                    change_counter += 1
                    entries.append(make_deletion_entry(
                        child, change_counter, context,
                    ))
                elif child.tag == qn("w:r"):
                    comment_counter = process_comment_ref(
                        child, context, comments_lookup, entries,
                        comment_counter,
                    )

    return entries, comment_counter


def _get_paragraph_context(paragraph) -> str:
    """Get the clean accepted-all text of a paragraph for context.

    Uses Adeu's get_visible_runs and get_run_text for the accepted-all
    view, prefixed with any numbering or list marker. Falls back to
    deleted text when the paragraph consists entirely of deletions
    (full-clause deletion), since the accepted-all view would be empty.

    Args:
        paragraph: A python-docx Paragraph object.

    Returns:
        The clean paragraph text, or deleted text as fallback.
    """
    prefix = get_paragraph_prefix(paragraph)
    runs = get_visible_runs(paragraph)
    text = "".join(get_run_text(r) for r in runs)
    context = prefix + text

    if context.strip():
        return context

    # Fallback: paragraph is entirely deleted content. Use deleted text
    # so downstream consumers have meaningful context for full-clause deletions.
    deleted_parts: list[str] = []
    for child in iter_effective_children(paragraph._element):
        if child.tag == qn("w:del"):
            deleted_parts.append(extract_del_text(child))
    return "".join(deleted_parts)
