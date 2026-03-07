"""Empty w:ins element cleaner for the atomic pipeline.

Detects and removes w:ins elements from a document body that contain
no text content. These empty insertions can appear after accept operations
remove nested w:del elements, leaving behind zero-width w:ins wrappers
that Word renders as invisible artifacts.

This module operates on a raw lxml body element and does NOT use
build_state_of_play(), Document(path), or .save().
"""

from docx.oxml.ns import qn
from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def clean_empty_ins_elements(body: etree._Element) -> int:
    """Find and remove empty w:ins elements from the document body.

    An empty w:ins is one that contains no descendant w:t elements with
    non-empty text content. This includes completely empty w:ins elements
    and those containing only empty w:r elements (runs with no text).

    Args:
        body: The document body element to clean.

    Returns:
        The number of empty w:ins elements removed.
    """
    empty_elements = _find_empty_ins_elements(body)
    for element in empty_elements:
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    return len(empty_elements)


def _find_empty_ins_elements(body: etree._Element) -> list[etree._Element]:
    """Collect all w:ins elements that have no text content.

    Walks the body using xpath for w:ins elements, then checks each
    for descendant w:t elements with non-empty text.

    Args:
        body: The document body element to search.

    Returns:
        List of empty w:ins elements to remove.
    """
    empty: list[etree._Element] = []
    for ins_element in body.iter(qn("w:ins")):
        if not _has_text_content(ins_element):
            empty.append(ins_element)
    return empty


def _has_text_content(element: etree._Element) -> bool:
    """Check if an element has any meaningful content (text or tracked changes).

    A w:ins is NOT empty if it contains either:
    - A descendant w:t with non-empty text, OR
    - A descendant w:del element (deletion inside insertion = layered markup)

    Args:
        element: The element to check for content.

    Returns:
        True if any meaningful content is found, False otherwise.
    """
    for text_element in element.iter(qn("w:t")):
        if text_element.text:
            return True
    # A w:ins wrapping a w:del is a deletion of inserted text --
    # this is valid layered tracked-change markup, not garbage.
    for _del_element in element.iter(qn("w:del")):
        return True
    return False
