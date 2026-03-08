"""AnchorMap -- clean-text position mapping and anchored edit application.

Maps 'accepted all' text positions back to OOXML Run elements with
tracked-change context. apply_anchored_edit auto-layers counter-proposals
when edits target text inside existing w:ins elements.

Extracted from local adeu fork (not in upstream adeu v0.7.0).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree

from src.anchor.anchor_helpers import (
    _counter_propose_full_insertion,
    _counter_propose_partial_insertion,
    apply_clean_text_edit,
    apply_mixed_context_edit,
    get_insertion_text,
    get_max_revision_id,
)
from adeu.redline.mapper import DocumentMapper, TextSpan

logger = logging.getLogger(__name__)


@dataclass
class AnchorSpan:
    """A span in the clean-text view mapped back to its OOXML context."""

    clean_start: int
    clean_end: int
    text: str
    run: Optional[Run]
    paragraph: Optional[Paragraph]
    ins_id: Optional[str] = None
    wrapper_element: Optional[etree._Element] = field(
        default=None, repr=False
    )


class AnchorMap:
    """Position map between the clean-text view and OOXML elements."""

    def __init__(self, doc: DocumentObject) -> None:
        """Build an AnchorMap from a Document object."""
        self.clean_mapper = DocumentMapper(doc, clean_view=True)
        self.spans: list[AnchorSpan] = []
        self._build_anchor_spans()

    @property
    def clean_text(self) -> str:
        """Return the clean (accepted-all) text view of the document."""
        return self.clean_mapper.full_text

    def _build_anchor_spans(self) -> None:
        """Convert clean_mapper TextSpans to AnchorSpans."""
        for text_span in self.clean_mapper.spans:
            if text_span.run is None:
                continue
            wrapper = _find_ins_wrapper(text_span) if text_span.ins_id else None
            self.spans.append(
                AnchorSpan(
                    clean_start=text_span.start,
                    clean_end=text_span.end,
                    text=text_span.text,
                    run=text_span.run,
                    paragraph=text_span.paragraph,
                    ins_id=text_span.ins_id,
                    wrapper_element=wrapper,
                )
            )

    def resolve_spans(self, start: int, end: int) -> list[AnchorSpan]:
        """Return all AnchorSpans overlapping [start, end) in clean text."""
        return [
            span
            for span in self.spans
            if span.clean_end > start and span.clean_start < end
        ]

    def find_match(self, target_text: str) -> tuple[int, int]:
        """Find target_text in clean text. Returns (start, length) or (-1, 0)."""
        return self.clean_mapper.find_match_index(target_text)


def _find_ins_wrapper(text_span: TextSpan) -> Optional[etree._Element]:
    """Walk up the lxml tree from a Run to find the containing w:ins."""
    if text_span.run is None:
        return None
    element = text_span.run._element
    parent = element.getparent()
    while parent is not None:
        if parent.tag == qn("w:ins"):
            return parent
        parent = parent.getparent()
    return None


def apply_anchored_edit(
    doc: DocumentObject,
    target_text: str,
    new_text: str,
    author: str,
    timestamp: str,
) -> None:
    """Apply an edit with auto-layering based on tracked-change context.

    For clean text: standard w:del + w:ins. For text inside a w:ins:
    counter-proposal (w:del nested inside w:ins + sibling w:ins).

    Raises ValueError if target_text is not found in the document.
    """
    anchor_map = AnchorMap(doc)
    start_idx, match_len = anchor_map.find_match(target_text)
    if start_idx == -1:
        raise ValueError(f"Target text not found: '{target_text[:50]}'")

    end_idx = start_idx + match_len
    context = classify_edit_context(anchor_map, start_idx, end_idx)
    body = doc.element.body
    next_id = get_max_revision_id(body) + 1

    if context == "clean_text":
        runs = anchor_map.clean_mapper.find_target_runs_by_index(
            start_idx, match_len,
        )
        if runs:
            apply_clean_text_edit(runs, new_text, author, timestamp, next_id)

    elif context == "inside_insertion":
        _apply_insertion_edit(
            anchor_map, start_idx, end_idx, target_text,
            new_text, author, timestamp, next_id,
        )

    elif context == "mixed":
        apply_mixed_context_edit(
            anchor_map, start_idx, end_idx,
            new_text, author, timestamp, next_id,
        )


def _apply_insertion_edit(
    anchor_map: AnchorMap,
    start_idx: int,
    end_idx: int,
    target_text: str,
    new_text: str,
    author: str,
    timestamp: str,
    next_id: int,
) -> None:
    """Route an inside-insertion edit to full or partial counter-proposal."""
    spans = anchor_map.resolve_spans(start_idx, end_idx)
    wrapper = spans[0].wrapper_element
    if wrapper is None:
        return

    full_ins_text = get_insertion_text(wrapper)
    if target_text == full_ins_text:
        _counter_propose_full_insertion(
            wrapper, author, timestamp, new_text, next_id,
        )
    else:
        _counter_propose_partial_insertion(
            wrapper, target_text, new_text, author, timestamp, next_id,
        )


def classify_edit_context(
    anchor_map: AnchorMap, start_idx: int, end_idx: int,
) -> str:
    """Classify edit as 'clean_text', 'inside_insertion', 'mixed', or 'no_match'."""
    affected = anchor_map.resolve_spans(start_idx, end_idx)
    if not affected:
        return "no_match"

    has_insertion = any(span.ins_id is not None for span in affected)
    has_clean = any(span.ins_id is None for span in affected)

    if has_insertion and not has_clean:
        return "inside_insertion"
    if has_clean and not has_insertion:
        return "clean_text"
    return "mixed"
