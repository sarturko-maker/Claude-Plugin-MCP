"""OOXML helpers for anchoring standalone comments to document content.

Provides functions for two comment anchoring modes:
- By tracked change: wraps a w:ins or w:del element with comment range markers
- By text match: finds a text string in a paragraph and wraps matching runs

Also provides standalone comment creation in comments.xml and commentsExtended.xml,
similar to add_reply_comment but WITHOUT paraIdParent (no thread parent).

Reuses OPC part management from reply_helpers.py. Range marker construction
follows the pattern from tests/phase2/comment_helpers.py attach_comment_to_range.
"""

from lxml import etree

from docx.opc.part import XmlPart
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from src.models.comment import CommentError
from src.negotiation.accept_helpers import find_tracked_change_element
from src.negotiation.reply_helpers import W15_NS


def anchor_comment_to_tracked_change(
    body: etree._Element, ooxml_id: str, comment_id: int
) -> None:
    """Anchor a comment to a tracked change element by wrapping it with range markers.

    Finds the w:ins or w:del by ooxml_id, then inserts commentRangeStart before
    it in the parent paragraph, commentRangeEnd after it, and a commentReference
    run after the range end.

    Args:
        body: The document body element.
        ooxml_id: The w:id attribute of the tracked change element.
        comment_id: The numeric comment ID for the range markers.

    Raises:
        CommentError: If the tracked change element is not found in the body.
    """
    element = find_tracked_change_element(body, ooxml_id)
    if element is None:
        raise CommentError(
            f"Tracked change element not found for ooxml_id={ooxml_id}"
        )

    parent = element.getparent()
    if parent is None:
        raise CommentError(
            f"Tracked change element has no parent for ooxml_id={ooxml_id}"
        )

    cid_str = str(comment_id)
    _insert_range_markers(parent, element, cid_str)


def anchor_comment_to_text(
    body: etree._Element, target_text: str, comment_id: int
) -> None:
    """Anchor a comment to a text string by finding it in a paragraph.

    Walks all paragraphs, concatenates run text, and checks for a match.
    If found in exactly one paragraph, wraps the matching runs with comment
    range markers. Raises CommentError on zero or multiple matches.

    Args:
        body: The document body element.
        target_text: The text string to find and anchor to.
        comment_id: The numeric comment ID for the range markers.

    Raises:
        CommentError: If text not found or found in multiple paragraphs.
    """
    matching_paragraphs = _find_paragraphs_containing_text(body, target_text)

    if len(matching_paragraphs) == 0:
        raise CommentError(f"Text not found in document: {target_text!r}")

    if len(matching_paragraphs) > 1:
        raise CommentError(
            f"Ambiguous text match -- {target_text!r} found in "
            f"{len(matching_paragraphs)} paragraphs"
        )

    paragraph = matching_paragraphs[0]
    anchors = _get_content_children(paragraph)
    if not anchors:
        raise CommentError(f"No content elements found in paragraph matching {target_text!r}")

    cid_str = str(comment_id)
    _insert_range_markers(paragraph, anchors[0], cid_str, end_element=anchors[-1])


def create_standalone_comment(
    comments_part: XmlPart,
    extended_part: XmlPart,
    comment_id: int,
    author: str,
    timestamp: str,
    text: str,
    para_id: str,
    initials: str | None = None,
) -> None:
    """Create a standalone comment in comments.xml and commentsExtended.xml.

    Unlike add_reply_comment, this creates a root-level comment with no
    paraIdParent. The done attribute is set to "0" (unresolved).
    If initials is provided, sets w:initials attribute on the comment element.

    Args:
        comments_part: The comments.xml OPC part.
        extended_part: The commentsExtended.xml OPC part.
        comment_id: The numeric comment ID.
        author: The comment author name.
        timestamp: ISO 8601 timestamp string.
        text: The comment text content.
        para_id: The unique paraId for this comment.
        initials: Optional author initials for the comment bubble in Word.
    """
    comment = OxmlElement("w:comment")
    comment.set(qn("w:id"), str(comment_id))
    comment.set(qn("w:author"), author)
    if initials is not None:
        comment.set(qn("w:initials"), initials)
    comment.set(qn("w:date"), timestamp)
    paragraph = OxmlElement("w:p")
    paragraph.set(qn("w14:paraId"), para_id)
    run = OxmlElement("w:r")
    text_elem = OxmlElement("w:t")
    text_elem.text = text
    run.append(text_elem)
    paragraph.append(run)
    comment.append(paragraph)
    comments_part.element.append(comment)

    nsmap = {"w15": W15_NS}
    comment_ex = etree.SubElement(
        extended_part.element, f"{{{W15_NS}}}commentEx", nsmap=nsmap
    )
    comment_ex.set(f"{{{W15_NS}}}paraId", para_id)
    comment_ex.set(f"{{{W15_NS}}}done", "0")


_CONTENT_TAGS = frozenset({qn("w:r"), qn("w:ins"), qn("w:del")})


def _get_content_children(paragraph: etree._Element) -> list[etree._Element]:
    """Get all content-bearing direct children of a paragraph.

    Returns direct child elements that are runs (w:r), tracked insertions
    (w:ins), or tracked deletions (w:del). This ensures comment range
    markers can anchor to text inside tracked change wrappers, not just
    to direct runs.
    """
    return [elem for elem in paragraph if elem.tag in _CONTENT_TAGS]


def _find_paragraphs_containing_text(
    body: etree._Element, target_text: str
) -> list[etree._Element]:
    """Find all paragraphs whose concatenated run text contains the target."""
    matches: list[etree._Element] = []
    for paragraph in body.iter(qn("w:p")):
        full_text = _get_paragraph_run_text(paragraph)
        if target_text in full_text:
            matches.append(paragraph)
    return matches


def _get_paragraph_run_text(paragraph: etree._Element) -> str:
    """Concatenate all w:t text from runs in a paragraph."""
    parts: list[str] = []
    for run in paragraph.iter(qn("w:r")):
        for text_elem in run.findall(qn("w:t")):
            if text_elem.text:
                parts.append(text_elem.text)
    return "".join(parts)


def _insert_range_markers(
    paragraph: etree._Element,
    start_element: etree._Element,
    comment_id: str,
    end_element: etree._Element | None = None,
) -> None:
    """Insert commentRangeStart/End and commentReference around target elements."""
    if end_element is None:
        end_element = start_element

    range_start = OxmlElement("w:commentRangeStart")
    range_start.set(qn("w:id"), comment_id)

    range_end = OxmlElement("w:commentRangeEnd")
    range_end.set(qn("w:id"), comment_id)

    ref_run = OxmlElement("w:r")
    ref = OxmlElement("w:commentReference")
    ref.set(qn("w:id"), comment_id)
    ref_run.append(ref)

    start_index = list(paragraph).index(start_element)
    paragraph.insert(start_index, range_start)

    end_index = list(paragraph).index(end_element)
    paragraph.insert(end_index + 1, range_end)
    paragraph.insert(end_index + 2, ref_run)
