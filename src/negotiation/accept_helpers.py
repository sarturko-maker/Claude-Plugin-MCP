"""OOXML element manipulation helpers for selective accept operations.

Provides low-level functions to find tracked change elements by ooxml_id,
accept insertions (unwrap w:ins), accept deletions (remove w:del), and
clean up empty parent wrappers. Also validates output file paths.

These functions operate on raw lxml elements from python-docx's Document
object. The patterns are derived from Adeu's _accept_changes_in_element
but targeted at specific elements rather than accepting all changes.
"""

from pathlib import Path

from docx.oxml.ns import qn
from lxml import etree

from src.models.accept import AcceptError


def find_tracked_change_element(
    body: etree._Element, ooxml_id: str
) -> etree._Element | None:
    """Find a w:ins or w:del element by its w:id attribute.

    Walks the entire element tree searching for tracked change elements
    with a matching w:id value. Returns the first match or None.

    Args:
        body: The document body element to search within.
        ooxml_id: The w:id attribute value to match (e.g., '201').

    Returns:
        The matching element, or None if not found.
    """
    for element in body.iter():
        if element.tag in (qn("w:ins"), qn("w:del")):
            if element.get(qn("w:id")) == ooxml_id:
                return element
    return None


def accept_element(element: etree._Element) -> None:
    """Accept a tracked change element by dispatching to the correct handler.

    Routes w:ins elements to _accept_insertion and w:del elements to
    _accept_deletion. Raises AcceptError for unrecognized element tags.

    Args:
        element: A w:ins or w:del element to accept.

    Raises:
        AcceptError: If the element tag is not w:ins or w:del.
    """
    if element.tag == qn("w:ins"):
        _accept_insertion(element)
    elif element.tag == qn("w:del"):
        _accept_deletion(element)
    else:
        raise AcceptError(f"Cannot accept element with tag: {element.tag}")


def _accept_insertion(ins_element: etree._Element) -> None:
    """Accept a w:ins by unwrapping: move children to parent, remove wrapper.

    Moves all child elements (runs) from the w:ins to the parent element
    at the same position, preserving document order. Then removes the
    now-empty w:ins wrapper. This makes the inserted text part of the
    clean document content.

    Args:
        ins_element: The w:ins element to accept.
    """
    parent = ins_element.getparent()
    index = list(parent).index(ins_element)
    children = list(ins_element)
    for i, child in enumerate(children):
        parent.insert(index + i, child)
    parent.remove(ins_element)


def _accept_deletion(del_element: etree._Element) -> None:
    """Accept a w:del by removing it entirely from the document.

    Removes the w:del element and all its content (the deleted text
    is permanently gone). After removal, checks if the parent element
    is a now-empty tracked change wrapper and cleans it up.

    Args:
        del_element: The w:del element to accept.
    """
    parent = del_element.getparent()
    parent.remove(del_element)
    _cleanup_empty_parent(parent)


def _cleanup_empty_parent(element: etree._Element) -> None:
    """Remove a tracked change wrapper if it has no remaining children.

    After accepting a nested element (e.g., w:del inside w:ins), the
    parent wrapper may be empty. An empty w:ins or w:del would appear
    as a zero-width artifact in Word, so it should be removed.

    Args:
        element: The parent element to check for emptiness.
    """
    if element is not None and element.tag in (qn("w:ins"), qn("w:del")):
        if len(element) == 0:
            grandparent = element.getparent()
            if grandparent is not None:
                grandparent.remove(element)


def validate_output_path(file_path: str) -> Path:
    """Validate that an output path is safe and writable.

    Checks for path traversal components (..), verifies the parent
    directory exists, and confirms the file extension is .docx.

    Args:
        file_path: String path for the output file.

    Returns:
        Resolved absolute Path to the validated output location.

    Raises:
        AcceptError: If the path contains traversal, parent directory
            does not exist, or extension is not .docx.
    """
    path = Path(file_path).resolve()
    raw_parts = Path(file_path).parts
    if ".." in raw_parts:
        raise AcceptError("Invalid output path")
    if not path.parent.exists():
        raise AcceptError(
            f"Output directory does not exist: {path.parent.name}"
        )
    if path.suffix.lower() != ".docx":
        raise AcceptError("Output must be a .docx file")
    return path
