"""Comment extraction from word/comments.xml and word/commentsExtended.xml.

Loads comments from a .docx document's comments relationship,
building a lookup dictionary keyed by comment ID. Each entry
contains the comment's author, date, full text content, and
paragraph paraId for thread correlation.

Also loads comment threading information from commentsExtended.xml,
which links reply comments to their parent via paraId/paraIdParent.

Used by the annotated extractor to emit CriticMarkup comment
markers and by the state-of-play builder for thread-aware display.
"""

from docx.document import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from lxml import etree

COMMENTS_EXTENDED_REL = (
    "http://schemas.microsoft.com/office/2011"
    "/relationships/commentsExtended"
)
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"


def load_comments(document: Document) -> dict[str, dict]:
    """Build a lookup dictionary of comments from word/comments.xml.

    Iterates the document's OPC relationships looking for the COMMENTS
    relationship type. For each w:comment element found, extracts the
    comment ID, author, date, text content, and paragraph paraId.

    Args:
        document: A python-docx Document object.

    Returns:
        Dictionary mapping comment ID (string) to a dict with keys:
        'author' (str), 'date' (str), 'text' (str), 'para_id' (str).
        Returns empty dict if the document has no comments relationship.
    """
    comments: dict[str, dict] = {}

    for rel in document.part.rels.values():
        if rel.reltype == RT.COMMENTS:
            for comment_element in rel.target_part.element:
                if comment_element.tag == qn("w:comment"):
                    comment_id = comment_element.get(qn("w:id"))
                    author = comment_element.get(qn("w:author")) or ""
                    date = comment_element.get(qn("w:date")) or ""
                    text = _extract_comment_text(comment_element)
                    para_id = _extract_para_id(comment_element)
                    comments[comment_id] = {
                        "author": author,
                        "date": date,
                        "text": text,
                        "para_id": para_id,
                    }
            break  # Only one COMMENTS relationship expected

    return comments


def load_comments_extended(document: Document) -> dict[str, dict]:
    """Load thread structure from word/commentsExtended.xml.

    Reads w15:commentEx elements from the commentsExtended OPC part,
    which store parent/child thread relationships and resolution status.
    The commentsExtended part may be a plain Part (not XmlPart), so
    we parse from the blob when the element attribute is not available.

    Args:
        document: A python-docx Document object.

    Returns:
        Dictionary mapping paraId (string) to a dict with keys:
        'para_id_parent' (str or None) and 'done' (bool).
        Returns empty dict if no commentsExtended relationship exists.
    """
    extended: dict[str, dict] = {}

    for rel in document.part.rels.values():
        if rel.reltype == COMMENTS_EXTENDED_REL:
            root = _get_part_root(rel.target_part)
            if root is None:
                break
            for entry in root:
                if "commentEx" in entry.tag:
                    para_id = entry.get(f"{{{W15_NS}}}paraId") or ""
                    parent = entry.get(f"{{{W15_NS}}}paraIdParent")
                    done = entry.get(f"{{{W15_NS}}}done") == "1"
                    extended[para_id] = {
                        "para_id_parent": parent,
                        "done": done,
                    }
            break  # Only one commentsExtended relationship expected

    return extended


def _get_part_root(part):
    """Get the lxml root element from an OPC part.

    Handles both XmlPart (has .element) and plain Part (has .blob).

    Args:
        part: An OPC part object.

    Returns:
        The lxml root element, or None if inaccessible.
    """
    if hasattr(part, "element"):
        return part.element
    if hasattr(part, "blob"):
        return etree.fromstring(part.blob)
    return None


def _extract_comment_text(comment_element) -> str:
    """Extract all text content from a w:comment element.

    Joins text from all w:t elements across all paragraphs and runs
    within the comment, separated by spaces.

    Args:
        comment_element: An lxml element with tag w:comment.

    Returns:
        The combined text content of the comment.
    """
    text_parts: list[str] = []

    for paragraph in comment_element.findall(qn("w:p")):
        for run in paragraph.findall(qn("w:r")):
            for text_element in run.findall(qn("w:t")):
                if text_element.text:
                    text_parts.append(text_element.text)

    return " ".join(text_parts)


def _extract_para_id(comment_element) -> str:
    """Extract the w14:paraId from a comment's first paragraph.

    The paraId is set on the w:p element inside the w:comment and is
    used to correlate comments with commentsExtended.xml entries for
    thread structure.

    Args:
        comment_element: An lxml element with tag w:comment.

    Returns:
        The paraId hex string, or empty string if not found.
    """
    paragraph = comment_element.find(qn("w:p"))
    if paragraph is not None:
        return paragraph.get(qn("w14:paraId")) or ""
    return ""
