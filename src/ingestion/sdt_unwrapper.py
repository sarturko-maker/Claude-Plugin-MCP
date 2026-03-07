"""Unwrap w:sdt (Structured Document Tag) wrappers in OOXML elements.

Word and other editors sometimes wrap tracked changes inside w:sdt elements.
For example, instead of:
    <w:p><w:ins>...</w:ins></w:p>

the XML may be:
    <w:p><w:sdt><w:sdtContent><w:ins>...</w:ins></w:sdtContent></w:sdt></w:p>

This module provides a generator that transparently unwraps SDT containers,
yielding the effective children regardless of whether they are wrapped or not.
All tracked-change walking code should use iter_effective_children() instead
of iterating element children directly.
"""

from collections.abc import Iterator

from docx.oxml.ns import qn
from lxml import etree


def iter_effective_children(element: etree._Element) -> Iterator[etree._Element]:
    """Yield effective child elements, unwrapping w:sdt containers.

    For each direct child of the element:
    - If it is a w:sdt, yields the children of its w:sdtContent instead.
    - Otherwise, yields the child directly.

    This handles the pattern where Word wraps tracked changes (w:ins, w:del,
    w:r) inside w:sdt > w:sdtContent, which would otherwise be invisible to
    parsers that only check direct children.

    SDT unwrapping is recursive: if an sdtContent itself contains another
    w:sdt, that is unwrapped too.

    Args:
        element: An lxml element whose children to iterate.

    Yields:
        Child elements with SDT wrappers transparently removed.
    """
    for child in element:
        if child.tag == qn("w:sdt"):
            sdt_content = child.find(qn("w:sdtContent"))
            if sdt_content is not None:
                yield from iter_effective_children(sdt_content)
        else:
            yield child
