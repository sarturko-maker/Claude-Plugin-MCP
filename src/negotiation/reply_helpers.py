"""OOXML helpers for constructing comment reply XML in .docx documents.

Provides low-level functions for creating threaded reply comments:
- Getting or creating the comments and commentsExtended OPC parts
- Generating unique comment IDs and paragraph IDs (paraId)
- Building and appending reply comment XML elements
- Anchoring reply comments in the document body inside the parent's range

Reply comments need both comments.xml / commentsExtended.xml entries AND
commentRangeStart/End/Reference anchors in document.xml. Word requires
body anchors for ALL comments (including replies) to render them.
"""

from lxml import etree

from docx.document import Document
from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.part import XmlPart
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

COMMENTS_EXTENDED_REL = (
    "http://schemas.microsoft.com/office/2011"
    "/relationships/commentsExtended"
)
COMMENTS_EXTENDED_CT = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.commentsExtended+xml"
)
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"


def get_or_create_comments_part(document: Document) -> XmlPart:
    """Get existing comments OPC part or create word/comments.xml."""
    for rel in document.part.rels.values():
        if rel.reltype == RT.COMMENTS:
            return rel.target_part

    package = document.part.package
    partname = package.next_partname("/word/comments%d.xml")
    xml_bytes = f"<w:comments {nsdecls('w')}>\n</w:comments>".encode("utf-8")
    comments_part = XmlPart(
        partname, CT.WML_COMMENTS, parse_xml(xml_bytes), package
    )
    package.parts.append(comments_part)
    document.part.relate_to(comments_part, RT.COMMENTS)
    return comments_part


def get_or_create_comments_extended_part(document: Document) -> XmlPart:
    """Get existing commentsExtended OPC part or create a new one.

    Handles the case where commentsExtended is a plain Part (not XmlPart)
    by upgrading it so elements can be appended.
    """
    for rel in document.part.rels.values():
        if rel.reltype == COMMENTS_EXTENDED_REL:
            target = rel.target_part
            if not hasattr(target, "element"):
                return _upgrade_plain_part(document, target)
            return target
    return _create_extended_part(document)


def _upgrade_plain_part(document: Document, part) -> XmlPart:
    """Upgrade a plain Part to XmlPart by re-creating with parsed blob."""
    root = etree.fromstring(part.blob)
    package = document.part.package
    xml_part = XmlPart(part.partname, part.content_type, root, package)
    if part in list(package.iter_parts()):
        package.parts.append(xml_part)
    for rel_key, rel in list(document.part.rels.items()):
        if rel.reltype == COMMENTS_EXTENDED_REL:
            document.part.rels[rel_key]._target = xml_part
            break
    return xml_part


def _create_extended_part(document: Document) -> XmlPart:
    """Create a fresh commentsExtended.xml OPC part with w15 namespace."""
    xml_str = (
        '<w15:commentsEx'
        ' xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"'
        ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
        ' mc:Ignorable="w15"></w15:commentsEx>'
    )
    package = document.part.package
    partname = package.next_partname("/word/commentsExtended%d.xml")
    root = parse_xml(xml_str.encode("utf-8"))
    ext_part = XmlPart(partname, COMMENTS_EXTENDED_CT, root, package)
    package.parts.append(ext_part)
    document.part.relate_to(ext_part, COMMENTS_EXTENDED_REL)
    return ext_part


def get_next_comment_id(comments_part: XmlPart) -> int:
    """Scan all w:comment elements and return max(id) + 1."""
    max_id = 0
    for comment in comments_part.element:
        if comment.tag == qn("w:comment"):
            cid = comment.get(qn("w:id"))
            if cid and cid.isdigit():
                max_id = max(max_id, int(cid))
    return max_id + 1


def collect_existing_para_ids(document: Document) -> set[str]:
    """Collect all paraId values from comments.xml and commentsExtended.xml.

    Used to avoid paraId collisions when adding new reply comments.
    """
    para_ids: set[str] = set()
    for rel in document.part.rels.values():
        if rel.reltype == RT.COMMENTS:
            for comment in rel.target_part.element:
                for para in comment.findall(qn("w:p")):
                    pid = para.get(qn("w14:paraId"))
                    if pid:
                        para_ids.add(pid)
    for rel in document.part.rels.values():
        if rel.reltype == COMMENTS_EXTENDED_REL:
            root = _get_root(rel.target_part)
            if root is not None:
                for entry in root:
                    pid = entry.get(f"{{{W15_NS}}}paraId")
                    if pid:
                        para_ids.add(pid)
    return para_ids


def _get_root(part):
    """Get lxml root from an OPC part (XmlPart or plain Part)."""
    if hasattr(part, "element"):
        return part.element
    if hasattr(part, "blob"):
        return etree.fromstring(part.blob)
    return None


def allocate_para_id(existing_ids: set[str], comment_id: int) -> str:
    """Generate a unique paraId for a new comment.

    Starts with deterministic formula f"{comment_id + 1000:08X}".
    If collision, increments until unique. Mutates existing_ids in place.
    """
    candidate = comment_id + 1000
    para_id = f"{candidate:08X}"
    while para_id in existing_ids:
        candidate += 1
        para_id = f"{candidate:08X}"
    existing_ids.add(para_id)
    return para_id


def add_reply_comment(
    comments_part: XmlPart,
    extended_part: XmlPart,
    comment_id: int,
    author: str,
    timestamp: str,
    text: str,
    parent_para_id: str,
    para_id: str,
    initials: str | None = None,
    ids_part: XmlPart | None = None,
    extensible_part: XmlPart | None = None,
) -> None:
    """Add a threaded reply to comments.xml and commentsExtended.xml.

    Creates w:comment with w14:paraId, and w15:commentEx with paraIdParent.
    If initials is provided, sets w:initials attribute on the comment element.

    Body anchors (commentRangeStart/End/Reference) must be added separately
    via anchor_reply_to_parent_range() — Word requires them for all comments.

    When ids_part and extensible_part are provided, also writes entries to
    commentsIds.xml and commentsExtensible.xml so Word displays the reply.
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

    # w15:commentEx -- uses raw lxml because OxmlElement lacks w15 namespace
    nsmap = {"w15": W15_NS}
    comment_ex = etree.SubElement(
        extended_part.element, f"{{{W15_NS}}}commentEx", nsmap=nsmap
    )
    comment_ex.set(f"{{{W15_NS}}}paraId", para_id)
    comment_ex.set(f"{{{W15_NS}}}paraIdParent", parent_para_id)
    comment_ex.set(f"{{{W15_NS}}}done", "0")

    # commentsIds.xml and commentsExtensible.xml entries
    if ids_part is not None and extensible_part is not None:
        from src.negotiation.comment_ids_helpers import (
            add_comment_extensible_entry,
            add_comment_id_entry,
            generate_durable_id,
        )
        durable_id = generate_durable_id(para_id)
        add_comment_id_entry(ids_part, para_id, durable_id)
        add_comment_extensible_entry(extensible_part, durable_id, timestamp)


def anchor_reply_to_parent_range(
    body: etree._Element, parent_ooxml_id: str, reply_comment_id: int
) -> None:
    """Anchor a reply comment in the document body inside the parent's range.

    Word requires commentRangeStart/End/Reference in document.xml for ALL
    comments, including threaded replies. This function finds the parent
    comment's existing range markers and nests the reply's markers inside them:

    - reply commentRangeStart inserted just after parent's commentRangeStart
    - reply commentRangeEnd inserted just before parent's commentRangeEnd
    - reply commentReference run inserted just after parent's commentReference run

    Args:
        body: The document body element (w:body).
        parent_ooxml_id: The w:id of the parent comment in document.xml.
        reply_comment_id: The numeric comment ID for the reply's markers.
    """
    parent_id_str = str(parent_ooxml_id)
    reply_id_str = str(reply_comment_id)

    parent_range_start = _find_marker(body, "w:commentRangeStart", parent_id_str)
    parent_range_end = _find_marker(body, "w:commentRangeEnd", parent_id_str)
    parent_ref_run = _find_comment_reference_run(body, parent_id_str)

    if parent_range_start is None or parent_range_end is None:
        return  # Parent has no body anchors — skip gracefully

    # Insert reply commentRangeStart right after parent's commentRangeStart
    parent_start_container = parent_range_start.getparent()
    start_idx = list(parent_start_container).index(parent_range_start)
    reply_range_start = OxmlElement("w:commentRangeStart")
    reply_range_start.set(qn("w:id"), reply_id_str)
    parent_start_container.insert(start_idx + 1, reply_range_start)

    # Insert reply commentRangeEnd right before parent's commentRangeEnd
    parent_end_container = parent_range_end.getparent()
    end_idx = list(parent_end_container).index(parent_range_end)
    reply_range_end = OxmlElement("w:commentRangeEnd")
    reply_range_end.set(qn("w:id"), reply_id_str)
    parent_end_container.insert(end_idx, reply_range_end)

    # Insert reply commentReference run right after parent's commentReference run
    if parent_ref_run is not None:
        ref_container = parent_ref_run.getparent()
        ref_idx = list(ref_container).index(parent_ref_run)
        reply_ref_run = OxmlElement("w:r")
        reply_ref = OxmlElement("w:commentReference")
        reply_ref.set(qn("w:id"), reply_id_str)
        reply_ref_run.append(reply_ref)
        ref_container.insert(ref_idx + 1, reply_ref_run)


def _find_marker(
    body: etree._Element, tag: str, comment_id: str
) -> etree._Element | None:
    """Find a commentRangeStart or commentRangeEnd element by w:id."""
    for elem in body.iter(qn(tag)):
        if elem.get(qn("w:id")) == comment_id:
            return elem
    return None


def _find_comment_reference_run(
    body: etree._Element, comment_id: str
) -> etree._Element | None:
    """Find the w:r element containing a commentReference with the given w:id."""
    for ref in body.iter(qn("w:commentReference")):
        if ref.get(qn("w:id")) == comment_id:
            return ref.getparent()
    return None
