"""Author extraction from tracked change metadata in .docx documents.

Walks OOXML elements (w:ins, w:del, w:comment) to discover all unique
authors and their change statistics. Returns an AuthorSummary that
Claude can use to assign party roles during negotiation.

Uses the same OOXML walking pattern established in Phase 3's annotated
extractor, but extracts structured metadata instead of CriticMarkup text.
"""

from collections import defaultdict

from docx import Document
from docx.oxml.ns import qn

from adeu.utils.docx import iter_document_parts

from src.ingestion.comment_loader import load_comments
from src.ingestion.sdt_unwrapper import iter_effective_children
from src.ingestion.validation import validate_docx_path
from src.models.party import AuthorInfo, AuthorSummary


def extract_authors(file_path: str) -> AuthorSummary:
    """Extract all unique authors and their change statistics from a .docx.

    Validates the file path, opens the document, and delegates to
    extract_authors_from_document for the actual extraction.

    Args:
        file_path: String path to the .docx document.

    Returns:
        AuthorSummary with authors sorted by total_changes descending.
        Returns an AuthorSummary with empty authors list if no tracked
        changes or comments are found.

    Raises:
        IngestionError: If the file path is invalid or not a .docx file.
    """
    validated_path = validate_docx_path(file_path)
    document = Document(str(validated_path))
    return extract_authors_from_document(document)


def extract_authors_from_document(document: Document) -> AuthorSummary:
    """Extract all unique authors from an already-opened Document.

    Walks all document parts for tracked change elements, loads comments,
    and builds an AuthorSummary with per-author insertion, deletion, and
    comment counts plus date ranges. Used by both extract_authors (which
    opens the file) and build_state_of_play (which shares the Document).

    Args:
        document: A python-docx Document object.

    Returns:
        AuthorSummary with authors sorted by total_changes descending.
    """
    author_stats = _collect_tracked_change_stats(document)
    _collect_comment_stats(document, author_stats)

    authors = _build_author_list(author_stats)
    return AuthorSummary(authors=authors)


def _collect_tracked_change_stats(
    document: Document,
) -> dict[str, dict]:
    """Walk all document parts and count tracked changes per author.

    For each paragraph element, checks for w:ins and w:del tags.
    Insertions are checked for nested deletions (counter-proposals).
    Each author's stats dict tracks insertions, deletions, and dates.

    Args:
        document: A python-docx Document object.

    Returns:
        Dictionary mapping author name (stripped) to stats dict with
        keys 'insertions', 'deletions', 'comments', 'dates'.
    """
    author_stats: dict[str, dict] = defaultdict(
        lambda: {"insertions": 0, "deletions": 0, "comments": 0, "dates": []}
    )

    for part in iter_document_parts(document):
        for paragraph in part.paragraphs:
            for child in iter_effective_children(paragraph._element):
                if child.tag == qn("w:ins"):
                    _record_insertion(child, author_stats)
                elif child.tag == qn("w:del"):
                    _record_deletion(child, author_stats)

    return author_stats


def _record_insertion(
    ins_element, author_stats: dict[str, dict]
) -> None:
    """Record an insertion element and any nested deletions.

    Increments the author's insertion count and records the date.
    Then checks for nested w:del elements (counter-proposals) and
    records those under the deletion author's stats.

    Args:
        ins_element: An lxml element with tag w:ins.
        author_stats: Mutable stats dictionary to update.
    """
    author = (ins_element.get(qn("w:author")) or "").strip()
    date = ins_element.get(qn("w:date")) or ""

    if author:
        author_stats[author]["insertions"] += 1
        if date:
            author_stats[author]["dates"].append(date)

    for nested in iter_effective_children(ins_element):
        if nested.tag == qn("w:del"):
            _record_deletion(nested, author_stats)


def _record_deletion(
    del_element, author_stats: dict[str, dict]
) -> None:
    """Record a deletion element (top-level or nested).

    Increments the author's deletion count and records the date.

    Args:
        del_element: An lxml element with tag w:del.
        author_stats: Mutable stats dictionary to update.
    """
    author = (del_element.get(qn("w:author")) or "").strip()
    date = del_element.get(qn("w:date")) or ""

    if author:
        author_stats[author]["deletions"] += 1
        if date:
            author_stats[author]["dates"].append(date)


def _collect_comment_stats(
    document: Document, author_stats: dict[str, dict]
) -> None:
    """Load comments and add comment counts to author stats.

    Reuses Phase 3's load_comments to get comment metadata, then
    increments each comment author's comment count and records dates.

    Args:
        document: A python-docx Document object.
        author_stats: Mutable stats dictionary to update.
    """
    comments = load_comments(document)
    for comment_data in comments.values():
        author = (comment_data.get("author") or "").strip()
        date = comment_data.get("date") or ""
        if author:
            author_stats[author]["comments"] += 1
            if date:
                author_stats[author]["dates"].append(date)


def _build_author_list(
    author_stats: dict[str, dict],
) -> list[AuthorInfo]:
    """Convert raw stats dictionaries into sorted AuthorInfo objects.

    Creates an AuthorInfo for each author with their counts and date
    range (earliest and latest dates). Sorts by total_changes descending.

    Args:
        author_stats: Dictionary mapping author name to stats dict.

    Returns:
        List of AuthorInfo objects sorted by total changes descending.
    """
    authors: list[AuthorInfo] = []

    for name, stats in author_stats.items():
        dates = sorted(stats["dates"])
        earliest = dates[0] if dates else ""
        latest = dates[-1] if dates else ""

        authors.append(
            AuthorInfo(
                name=name,
                insertion_count=stats["insertions"],
                deletion_count=stats["deletions"],
                comment_count=stats["comments"],
                earliest_date=earliest,
                latest_date=latest,
            )
        )

    authors.sort(key=lambda a: a.total_changes, reverse=True)
    return authors
