"""Surgical edit orchestrator for word-level tracked changes.

Main entry point: apply_edits_surgically() processes each edit through
word-level diffing when possible, delegating to Adeu's wholesale
engine.apply_edits() for edge cases (multi-paragraph, nested insert,
pure deletion, newlines in new_text, reconstruction mismatch).

Uses three-layer matching (full mapper, clean mapper, PlainTextIndex)
for resilient target text location. Rebuilds the mapper after each
successful DOM surgery so subsequent edits see the current DOM.

Ported from ~/vibe-legal-redliner/python/pipeline.py (lines 679-803).

Usage:
    from src.pipeline.surgical_edit import apply_edits_surgically

    engine = RedlineEngine(doc_stream, author="Client Firm")
    applied, skipped = apply_edits_surgically(engine, edits)
"""

import logging

from adeu import DocumentEdit

from src.pipeline.first_pass_result import EditOutcome
from src.pipeline.surgical_helpers import (
    attach_comment_to_elements,
    check_post_match_delegation,
    check_pre_match_delegation,
    delegate_wholesale,
    find_match_three_layer,
    perform_dom_surgery,
    rebuild_mapper,
)
from src.pipeline.word_diff import diff_words, verify_reconstruction
from src.pipeline.word_diff_compensations import (
    check_rewrite_ratio,
    deduplicate_edits,
    normalize_edit_whitespace,
    strip_formatting_markers,
    strip_redundant_clause_number,
)
from src.pipeline.word_diff_elements import (
    build_char_format_map,
    build_diff_elements,
)

logger = logging.getLogger(__name__)


def apply_edits_surgically(
    engine,
    edits: list[DocumentEdit],
    author_config=None,
) -> tuple[list[EditOutcome], list[EditOutcome]]:
    """Apply edits using word-level diff, falling back to wholesale.

    Processes edits one at a time, sorted by target_text length descending
    (longest first to avoid substring overlap). For each edit, checks
    delegation conditions and either applies surgical DOM surgery or
    delegates to engine.apply_edits().

    Returns (applied_outcomes, skipped_outcomes).
    """
    applied: list[EditOutcome] = []
    skipped: list[EditOutcome] = []

    deduped_edits = deduplicate_edits(edits)
    sorted_edits = sorted(
        deduped_edits,
        key=lambda e: len(e.target_text) if e.target_text else 0,
        reverse=True,
    )

    for edit in sorted_edits:
        outcome = _process_single_edit(engine, edit)
        if outcome.status == "applied":
            applied.append(outcome)
        else:
            skipped.append(outcome)

    return applied, skipped


def _process_single_edit(
    engine,
    edit: DocumentEdit,
) -> EditOutcome:
    """Process a single edit through surgical or wholesale path.

    Returns an EditOutcome with method and reason populated.
    """
    target_text, new_text = normalize_edit_whitespace(
        edit.target_text or "", edit.new_text or "",
    )

    pre_match_reason = check_pre_match_delegation(new_text)
    if pre_match_reason is not None:
        return delegate_wholesale(engine, edit, pre_match_reason)

    mapper, start_idx, match_len = find_match_three_layer(
        engine, target_text,
    )
    if start_idx == -1:
        return _build_skipped_outcome(edit, "no_match")

    target_runs = mapper.find_target_runs_by_index(start_idx, match_len)
    if not target_runs:
        return _build_skipped_outcome(edit, "no_runs_resolved")

    post_delegation = check_post_match_delegation(
        engine, edit, target_runs,
    )
    if post_delegation is not None:
        return post_delegation

    return _apply_surgical_diff(
        engine, edit, target_runs, new_text, match_len,
    )


def _apply_surgical_diff(
    engine,
    edit: DocumentEdit,
    target_runs: list,
    new_text: str,
    match_len: int,
) -> EditOutcome:
    """Apply word-level diff to target runs and perform DOM surgery.

    Returns an EditOutcome with method='surgical' on success, or
    delegates to wholesale on reconstruction mismatch.
    """
    runs_plain_text = "".join(run.text or "" for run in target_runs)
    clean_new_text = strip_formatting_markers(new_text)

    parent_p = target_runs[0]._element.getparent()
    clean_new_text = strip_redundant_clause_number(clean_new_text, parent_p)

    if runs_plain_text == clean_new_text:
        return _build_skipped_outcome(edit, "no_change")

    diffs = diff_words(runs_plain_text, clean_new_text)

    if not verify_reconstruction(diffs, clean_new_text):
        logger.warning(
            "Reconstruction mismatch for target '%s' -- falling back",
            edit.target_text[:50],
        )
        return delegate_wholesale(engine, edit, "reconstruction_mismatch")

    reason = ""
    ratio = check_rewrite_ratio(runs_plain_text, clean_new_text)
    if ratio > 0.7:
        reason = f"heavy_rewrite:{ratio:.0%}"

    char_map = build_char_format_map(target_runs, match_len)
    new_elements = build_diff_elements(diffs, char_map, engine)

    if not new_elements:
        return _build_skipped_outcome(edit, "no_elements_built")

    parent_element = target_runs[0]._element.getparent()
    perform_dom_surgery(target_runs, new_elements)

    if edit.comment:
        attach_comment_to_elements(
            engine, parent_element, new_elements, edit.comment,
        )

    rebuild_mapper(engine.mapper)
    engine.clean_mapper = None

    return EditOutcome(
        target_text=edit.target_text,
        new_text=edit.new_text,
        comment=edit.comment,
        status="applied",
        method="surgical",
        reason=reason,
    )


def _build_skipped_outcome(
    edit: DocumentEdit,
    reason: str,
) -> EditOutcome:
    """Build a skipped EditOutcome with the given reason."""
    return EditOutcome(
        target_text=edit.target_text,
        new_text=edit.new_text,
        comment=edit.comment,
        status="skipped",
        reason=reason,
    )
