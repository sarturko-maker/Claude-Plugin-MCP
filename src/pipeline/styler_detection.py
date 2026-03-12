"""Styler edge-case detection for formatting review.

Determines which w:ins elements need LLM formatting review. Adeu handles
inline text amendments correctly, but has known formatting limitations
for structural insertions. Each check targets a specific failure mode.

The main entry point is needs_styler_review(), called per w:ins element.
Only elements returning True get extracted as triplets for Claude to fix.

Edge cases covered:
1. Tables — formatting inheritance unreliable in table cells
2. Numbered lists — numbering format, indentation, restart vs continue
3. Style mismatches — inserted run font/size differs from paragraph default
4. Mixed formatting boundaries — adjacent bold/italic/underline inheritance
5. Definition lists / hanging indents — sub-clause numbering (via numPr)
6. Cross-references / bookmarks / field codes — structural elements
"""

from docx.oxml.ns import qn
from lxml import etree


def needs_styler_review(
    ins_element: etree._Element,
    paragraph: etree._Element,
) -> bool:
    """Check if a w:ins element needs Styler formatting review.

    Returns True for edge cases where Adeu's formatting is fragile.
    Returns False for simple inline text amendments where Adeu
    correctly inherits formatting from the surrounding content.

    Args:
        ins_element: A w:ins element to evaluate.
        paragraph: The w:p paragraph containing this insertion.

    Returns:
        True if this insertion needs Styler review.
    """
    if _is_inside_table(paragraph):
        return True

    if _has_numbering(paragraph):
        return True

    if _has_style_mismatch(ins_element, paragraph):
        return True

    if _at_formatting_boundary(ins_element, paragraph):
        return True

    if _has_field_or_bookmark(ins_element):
        return True

    return False


def _is_inside_table(element: etree._Element) -> bool:
    """Check if an element is nested inside a w:tbl (table) element."""
    ancestor = element.getparent()
    while ancestor is not None:
        if ancestor.tag == qn("w:tbl"):
            return True
        ancestor = ancestor.getparent()
    return False


def _has_numbering(paragraph: etree._Element) -> bool:
    """Check if a paragraph has numbering properties (w:numPr).

    Covers both regular numbered lists (1, 2, 3) and definition-style
    sub-clauses like (a), (b), (i), (ii) — all use w:numPr in OOXML.
    Adeu may not correctly inherit numbering format, indentation level,
    or restart vs continue numbering.
    """
    ppr = paragraph.find(qn("w:pPr"))
    if ppr is None:
        return False
    return ppr.find(qn("w:numPr")) is not None


def _has_style_mismatch(
    ins_element: etree._Element,
    paragraph: etree._Element,
) -> bool:
    """Check if inserted runs reference a different font than the paragraph.

    Compares font-family/size in w:ins runs' w:rPr against paragraph
    default w:rPr. A mismatch means Adeu inherited the wrong style.
    """
    para_fonts = _get_paragraph_default_fonts(paragraph)
    if not para_fonts:
        return False

    for run in ins_element.iter(qn("w:r")):
        run_fonts = _get_run_fonts(run)
        if not run_fonts:
            continue
        if run_fonts != para_fonts:
            return True

    return False


def _get_paragraph_default_fonts(
    paragraph: etree._Element,
) -> dict[str, str]:
    """Extract paragraph default font-family and font-size from w:pPr/w:rPr."""
    ppr = paragraph.find(qn("w:pPr"))
    if ppr is None:
        return {}
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        return {}
    return _extract_font_props(rpr)


def _get_run_fonts(run: etree._Element) -> dict[str, str]:
    """Extract a run's font-family and font-size from its w:rPr."""
    rpr = run.find(qn("w:rPr"))
    if rpr is None:
        return {}
    return _extract_font_props(rpr)


def _extract_font_props(rpr: etree._Element) -> dict[str, str]:
    """Extract font-family (w:rFonts ascii) and font-size (w:sz) from w:rPr."""
    props: dict[str, str] = {}
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is not None:
        ascii_font = rfonts.get(qn("w:ascii"))
        if ascii_font:
            props["ascii"] = ascii_font
    sz = rpr.find(qn("w:sz"))
    if sz is not None:
        val = sz.get(qn("w:val"))
        if val:
            props["sz"] = val
    return props


_FORMATTING_TAGS = frozenset([qn("w:b"), qn("w:i"), qn("w:u")])


def _at_formatting_boundary(
    ins_element: etree._Element,
    paragraph: etree._Element,
) -> bool:
    """Check if w:ins sits adjacent to a bold/italic/underline run.

    Adeu may incorrectly inherit or lose formatting at these boundaries.
    """
    prev = ins_element.getprevious()
    if prev is not None and _run_has_formatting(prev):
        return True

    nxt = ins_element.getnext()
    if nxt is not None and _run_has_formatting(nxt):
        return True

    return False


def _run_has_formatting(element: etree._Element) -> bool:
    """Check if element has bold/italic/underline (checks w:ins/w:del children too)."""
    if element.tag == qn("w:r"):
        return _rpr_has_formatting(element)

    # Check inside w:ins or w:del wrappers
    if element.tag in (qn("w:ins"), qn("w:del")):
        for run in element.iter(qn("w:r")):
            if _rpr_has_formatting(run):
                return True

    return False


def _rpr_has_formatting(run: etree._Element) -> bool:
    """Check if a w:r run's rPr contains bold, italic, or underline."""
    rpr = run.find(qn("w:rPr"))
    if rpr is None:
        return False
    return any(rpr.find(tag) is not None for tag in _FORMATTING_TAGS)


_FIELD_TAGS = frozenset([
    qn("w:bookmarkStart"),
    qn("w:fldSimple"),
    qn("w:fldChar"),
])


def _has_field_or_bookmark(ins_element: etree._Element) -> bool:
    """Check if w:ins contains bookmarks, field codes, or cross-references."""
    for tag in _FIELD_TAGS:
        if ins_element.find(f".//{tag}") is not None:
            return True
    return False
