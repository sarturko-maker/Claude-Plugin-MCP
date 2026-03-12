"""Helper functions for the surgical edit orchestrator.

Provides three-layer matching, delegation checks, DOM surgery, comment
attachment, and mapper rebuild. These are internal helpers used by
surgical_edit.py -- not part of the public API.

Split from surgical_edit.py to comply with the 200-line file limit.

Usage:
    Internal use only -- imported by src.pipeline.surgical_edit.
"""

import logging

from adeu import DocumentEdit
from adeu.anchor import apply_anchored_edit
from adeu.redline.mapper import DocumentMapper

from src.pipeline.first_pass_result import EditOutcome
from src.pipeline.plain_text_index import PlainTextIndex

logger = logging.getLogger(__name__)


def check_pre_match_delegation(new_text: str) -> str | None:
    """Check delegation conditions that don't require matching.

    Returns a reason string if delegation is needed, None otherwise.
    The caller should use delegate_wholesale() with the returned reason.
    """
    if not new_text or new_text.isspace():
        return "pure_deletion"

    if "\n" in new_text:
        return "newline_in_new_text"

    return None


def find_match_three_layer(
    engine,
    target_text: str,
) -> tuple[object, int, int]:
    """Try full mapper, clean mapper, then PlainTextIndex to find target.

    Three-layer matching reduces false skip rate when AI's target_text
    includes formatting markers or CriticMarkup that doesn't match
    the mapper's full_text exactly.

    Returns (active_mapper, start_idx, match_len). If no match found,
    returns (None, -1, 0).
    """
    mapper = engine.mapper
    start_idx, match_len = mapper.find_match_index(target_text)
    if start_idx != -1:
        return mapper, start_idx, match_len

    if not engine.clean_mapper:
        engine.clean_mapper = DocumentMapper(engine.doc, clean_view=True)
    start_idx, match_len = engine.clean_mapper.find_match_index(target_text)
    if start_idx != -1:
        return engine.clean_mapper, start_idx, match_len

    pti = PlainTextIndex(engine.mapper)
    start_idx, match_len = pti.find_match(target_text)
    if start_idx != -1:
        return engine.mapper, start_idx, match_len

    return None, -1, 0


def check_post_match_delegation(
    engine,
    edit: DocumentEdit,
    target_runs: list,
) -> EditOutcome | None:
    """Check delegation conditions that require resolved target runs.

    Checks for multi-paragraph spans and nested insertions.
    Returns an EditOutcome if delegation is needed, None otherwise.
    """
    parents = {
        id(run._element.getparent())
        for run in target_runs
        if run._element.getparent() is not None
    }
    if len(parents) > 1:
        return delegate_wholesale(engine, edit, "multi_paragraph")

    for run in target_runs:
        parent = run._element.getparent()
        if parent is not None and parent.tag.endswith("}ins"):
            return _apply_anchored_nested_insert(engine, edit)

    return None


def _apply_anchored_nested_insert(
    engine,
    edit: DocumentEdit,
) -> EditOutcome:
    """Route a nested-insert edit through apply_anchored_edit.

    Uses Adeu's anchor module to auto-layer a counter-proposal on top
    of the existing w:ins element, preserving the counterparty's markup
    and producing correct OOXML nesting (w:del inside w:ins + sibling w:ins).

    After a successful anchored edit, rebuilds the mapper so subsequent
    edits see the updated DOM.
    """
    target_text = edit.target_text or ""
    new_text = edit.new_text or ""

    try:
        apply_anchored_edit(
            engine.doc, target_text, new_text,
            engine.author, engine.timestamp,
        )
        status = "applied"
    except (ValueError, IndexError) as exc:
        logger.warning(
            "Anchored edit failed for '%s': %s -- falling back",
            target_text[:50], exc,
        )
        return delegate_wholesale(engine, edit, "nested_insert")

    rebuild_mapper(engine.mapper)
    engine.clean_mapper = None

    return EditOutcome(
        target_text=edit.target_text,
        new_text=edit.new_text,
        comment=edit.comment,
        status=status,
        method="anchored:nested_insert",
    )


def delegate_wholesale(
    engine,
    edit: DocumentEdit,
    reason: str,
) -> EditOutcome:
    """Delegate edit to engine.apply_edits() and build outcome."""
    applied_count, _ = engine.apply_edits([edit])
    status = "applied" if applied_count > 0 else "skipped"

    return EditOutcome(
        target_text=edit.target_text,
        new_text=edit.new_text,
        comment=edit.comment,
        status=status,
        method=f"wholesale:{reason}",
    )


def attach_comment_to_elements(
    engine,
    parent_element,
    new_elements: list,
    comment_text: str,
) -> None:
    """Attach a comment spanning the new surgical elements.

    Uses engine._attach_comment to add a comment anchored to the first
    and last new elements within the parent paragraph. This replicates
    the comment attachment that engine.apply_edits() handles automatically.

    Coupling: adeu.redline.engine.RedlineEngine._attach_comment
    Verified against: Adeu v0.7.0
    """
    if not new_elements or not comment_text:
        return
    first_elem = new_elements[0]
    last_elem = new_elements[-1]
    engine._attach_comment(
        parent_element, first_elem, last_elem, comment_text,
    )


def perform_dom_surgery(target_runs: list, new_elements: list) -> None:
    """Replace target runs with new diff-generated OOXML elements.

    Inserts new elements before the first target run, then removes
    all old target runs from their parent paragraphs.
    """
    first_run_elem = target_runs[0]._element
    parent = first_run_elem.getparent()
    insert_idx = list(parent).index(first_run_elem)

    for i, elem in enumerate(new_elements):
        parent.insert(insert_idx + i, elem)

    for run in target_runs:
        r_parent = run._element.getparent()
        if r_parent is not None:
            r_parent.remove(run._element)


def rebuild_mapper(mapper) -> None:
    """Rebuild mapper's internal state after DOM surgery.

    Calls mapper._build_map() which is a private method on Adeu's
    DocumentMapper. This is fragile coupling documented per RESEARCH
    pitfall 7. If Adeu renames this method, update here only.

    Coupling: adeu.redline.mapper.DocumentMapper._build_map()
    Verified against: Adeu v0.7.0
    """
    mapper._build_map()
