"""Deterministic extraction of client-authored paragraphs and fragment splicing.

Provides two functions:
- extract_client_triplets: Walks the document body, finds paragraphs with
  client-authored tracked changes (w:ins or w:del), and serializes each
  with its neighbors as raw OOXML strings.
- splice_corrected_fragments: Takes corrected OOXML fragments and replaces
  the original paragraphs in the document, processing in reverse index
  order to avoid position drift.

These functions are deterministic Python -- no LLM calls. The LLM step
happens in the StylerCallback between extraction and splicing.

Usage:
    from src.pipeline.styler_extraction import (
        extract_client_triplets,
        splice_corrected_fragments,
    )

    triplets = extract_client_triplets("output.docx", "Client Firm")
    fragments = styler.fix_formatting(triplets)
    splice_corrected_fragments("output.docx", "output.docx", fragments)
"""

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

from src.pipeline.styler import OoxmlFragment, OoxmlTriplet
from src.pipeline.styler_detection import needs_styler_review


def extract_client_triplets(
    document_path: str,
    client_author: str,
) -> list[OoxmlTriplet]:
    """Extract client-authored paragraphs needing formatting review.

    Only extracts paragraphs where Adeu's formatting is unreliable:
    (a) Paragraph-level insertions (wrong font/style inheritance)
    (b) Table content (formatting inheritance unreliable in cells)
    (c) Numbered lists and definition sub-clauses (numbering/indent)
    (d) Style mismatches (inserted font differs from paragraph default)
    (e) Mixed formatting boundaries (adjacent bold/italic/underline)
    (f) Cross-references, bookmarks, and field codes

    Skips simple inline text amendments — Adeu handles those correctly.

    Args:
        document_path: Path to the .docx document to extract from.
        client_author: Author name to match against w:author attributes.

    Returns:
        List of OoxmlTriplet, one per qualifying paragraph.
    """
    document = Document(document_path)
    body = document.element.body
    paragraphs = list(body.iter(qn("w:p")))
    triplets: list[OoxmlTriplet] = []

    for idx, para in enumerate(paragraphs):
        if not _paragraph_needs_styler_review(para, client_author):
            continue

        above = _serialize_paragraph(paragraphs[idx - 1]) if idx > 0 else ""
        target = _serialize_paragraph(para)
        below = (
            _serialize_paragraph(paragraphs[idx + 1])
            if idx < len(paragraphs) - 1
            else ""
        )

        triplets.append(OoxmlTriplet(
            paragraph_above=above,
            target_paragraph=target,
            paragraph_below=below,
            paragraph_index=idx,
        ))

    return triplets


def splice_corrected_fragments(
    document_path: str,
    output_path: str,
    fragments: list[OoxmlFragment],
) -> None:
    """Replace paragraphs in the document with corrected OOXML fragments.

    Processes fragments in reverse index order (highest paragraph_index
    first) to avoid position drift when earlier replacements shift
    subsequent indices.

    Args:
        document_path: Path to the .docx document to modify.
        output_path: Path to save the modified document.
        fragments: Corrected OOXML fragments to splice in.
    """
    document = Document(document_path)
    body = document.element.body
    paragraphs = list(body.iter(qn("w:p")))

    sorted_fragments = sorted(
        fragments, key=lambda f: f.paragraph_index, reverse=True,
    )

    for fragment in sorted_fragments:
        new_element = etree.fromstring(fragment.corrected_xml.encode())
        old_element = paragraphs[fragment.paragraph_index]
        old_element.getparent().replace(old_element, new_element)

    document.save(output_path)


def _paragraph_needs_styler_review(
    paragraph: etree._Element,
    client_author: str,
) -> bool:
    """Check if a paragraph needs Styler formatting review.

    Returns True for paragraphs containing client-authored w:ins
    elements that trigger any edge-case detector. Two paths:
    1. Paragraph-level insertion — parent is w:ins (always review).
    2. Inline w:ins elements — checked individually against the
       full edge-case suite in styler_detection.needs_styler_review().

    Simple inline text amendments where formatting is inherited
    correctly are skipped.

    Args:
        paragraph: An lxml element representing a w:p paragraph.
        client_author: Author name to match.

    Returns:
        True if this paragraph needs Styler review.
    """
    parent = paragraph.getparent()

    # Case 1: paragraph-level insertion (w:ins wraps the whole w:p)
    if parent is not None and parent.tag == qn("w:ins"):
        if parent.get(qn("w:author")) == client_author:
            return True

    # Case 2: check each client w:ins against edge-case detectors
    for ins in paragraph.iter(qn("w:ins")):
        if ins.get(qn("w:author")) != client_author:
            continue
        if needs_styler_review(ins, paragraph):
            return True

    return False


def _serialize_paragraph(paragraph: etree._Element) -> str:
    """Serialize a paragraph element to a raw OOXML string.

    Args:
        paragraph: An lxml element representing a w:p paragraph.

    Returns:
        The paragraph serialized as a UTF-8 XML string.
    """
    return etree.tostring(paragraph, encoding="unicode")
