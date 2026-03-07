"""Compensation functions for word-level diff pipeline.

Ported from ~/vibe-legal-redliner/python/pipeline.py. Each function
addresses a specific Adeu behaviour or AI output quirk discovered
through production use with real legal documents:

1. strip_formatting_markers -- removes ** and _ markers from AI output
2. normalize_edit_whitespace -- normalizes tabs to spaces
3. deduplicate_edits -- removes overlapping edits
4. check_rewrite_ratio -- detects heavy rewrites (>70% changed)
5. strip_redundant_clause_number -- prevents double numbering

Usage:
    from src.pipeline.word_diff_compensations import (
        strip_formatting_markers,
        normalize_edit_whitespace,
        deduplicate_edits,
        check_rewrite_ratio,
        strip_redundant_clause_number,
    )
"""

import re

from adeu import DocumentEdit
from docx.oxml.ns import qn

from src.pipeline.word_diff import diff_words


def strip_formatting_markers(text: str) -> str:
    """Strip ** (bold) and _ (italic) formatting markers from text.

    Adeu's mapper decorates full_text with ** and _ markers. The AI may
    echo these in new_text. Word-level diff inserts text literally without
    parsing markdown, so markers must be stripped before diffing.

    Preserves underscores between word characters (snake_case) since those
    are not italic markers.
    """
    # Strip balanced bold markers (keep inner text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # Strip remaining unbalanced **
    text = text.replace("**", "")
    # Strip balanced italic markers at word boundaries (avoid snake_case)
    text = re.sub(r"(?<![a-zA-Z0-9])_(.+?)_(?![a-zA-Z0-9])", r"\1", text)
    return text


def normalize_edit_whitespace(
    target_text: str,
    new_text: str,
) -> tuple[str, str]:
    """Normalize tab characters to spaces and strip trailing whitespace.

    Adeu's get_run_text() converts <w:tab/> to space, but literal tab
    in <w:t> passes through. The AI sees tab in extracted text but returns
    spaces in new_text, causing spurious whitespace-only tracked changes.

    Returns (clean_target, clean_new) with tabs replaced and trailing
    whitespace removed.
    """
    clean_target = target_text.replace("\t", " ").rstrip() if target_text else target_text
    clean_new = new_text.replace("\t", " ").rstrip() if new_text else new_text
    return clean_target, clean_new


def deduplicate_edits(
    edits: list[DocumentEdit],
) -> list[DocumentEdit]:
    """Remove edits with overlapping target_text to prevent double insertions.

    Sorts by target_text length (longest first). For each edit, checks
    whether its target_text is a substring of (or contains) an already-kept
    edit's target_text. If so, the shorter edit is dropped.

    The AI sometimes returns overlapping edits for the same paragraph.
    While mapper rebuild after each edit usually prevents double-application,
    edge cases with fuzzy matching can slip through.
    """
    if len(edits) <= 1:
        return edits

    sorted_edits = sorted(
        edits, key=lambda e: len(e.target_text), reverse=True,
    )
    kept: list[DocumentEdit] = []
    consumed_targets: list[str] = []

    for edit in sorted_edits:
        target = edit.target_text
        is_duplicate = _is_overlapping_target(target, consumed_targets)
        if not is_duplicate:
            kept.append(edit)
            consumed_targets.append(target)

    return kept


def check_rewrite_ratio(old_text: str, new_text: str) -> float:
    """Calculate ratio of changed characters to total old characters.

    Runs diff_words on the texts and measures how much changed.
    Returns a float between 0.0 (identical) and ~1.0 (total rewrite).
    A ratio above 0.7 indicates a heavy rewrite where the AI replaced
    most of the original text instead of making minimal word-level edits.
    """
    diffs = diff_words(old_text, new_text)
    return _compute_ratio_from_diffs(diffs)


def strip_redundant_clause_number(
    new_text: str,
    paragraph_element,
) -> str:
    """Strip leading clause numbers when the paragraph has auto-numbering.

    Checks for <w:numPr> in the paragraph's properties. If present, the
    paragraph auto-generates its number, so any leading number in new_text
    (e.g., '10. ', '10.1 ', '(a) ') would cause double numbering.

    The paragraph_element parameter is an lxml element (w:p) from the
    document XML.
    """
    if not new_text or paragraph_element is None:
        return new_text

    if not _has_auto_numbering(paragraph_element):
        return new_text

    return _strip_leading_number_pattern(new_text)


# -- Private helpers --------------------------------------------------------


def _is_overlapping_target(
    target: str,
    consumed_targets: list[str],
) -> bool:
    """Check if target overlaps with any previously consumed target."""
    for prev_target in consumed_targets:
        if target in prev_target or prev_target in target:
            return True
    return False


def _compute_ratio_from_diffs(
    diffs: list[tuple[int, str]],
) -> float:
    """Compute rewrite ratio from diff segments.

    Ratio = changed_chars / (total_old_chars * 2), where:
    - total_old_chars = EQUAL + DELETE text length
    - changed_chars = DELETE + INSERT text length
    """
    total_old = sum(len(t) for op, t in diffs if op <= 0)
    changed = sum(len(t) for op, t in diffs if op != 0)
    if total_old == 0:
        return 0.0
    return changed / (total_old * 2)


def _has_auto_numbering(paragraph_element) -> bool:
    """Check whether a paragraph element has <w:numPr> auto-numbering."""
    pPr = paragraph_element.find(qn("w:pPr"))
    if pPr is None:
        return False
    return pPr.find(qn("w:numPr")) is not None


def _strip_leading_number_pattern(new_text: str) -> str:
    """Strip leading clause number patterns from text.

    Handles: '10. ', '10.1 ', '10.1. ', '(a) ', '(iv) ', '(A) ',
    'Section 10. ', 'Article 10. ', 'Clause 10. '.
    """
    stripped = re.sub(
        r"^(?:"
        r"(?:Section|Article|Clause)\s+)?"  # Optional prefix
        r"(?:\d+(?:\.\d+)*\.?\s*"  # '10.' or '10.1.' or '10 '
        r"|\([a-z]+\)\s*"  # '(a)' or '(iv)'
        r"|\([A-Z]+\)\s*"  # '(A)' or '(IV)'
        r"|\([ivxlcdm]+\)\s*"  # '(iv)' roman
        r")",
        "",
        new_text,
    )
    return stripped if stripped else new_text
