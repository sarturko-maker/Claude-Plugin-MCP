"""OOXML helpers for commentsIds.xml and commentsExtensible.xml parts.

Word requires four comment-related parts to be in sync for comments to
display correctly:
  1. comments.xml — the comment content
  2. commentsExtended.xml — thread structure (paraIdParent, done)
  3. commentsIds.xml — maps paraId to durableId (w16cid namespace)
  4. commentsExtensible.xml — durableId to dateUtc (w16cex namespace)

Missing entries in (3) or (4) cause Word to silently hide comments,
especially reply comments in threaded conversations.

This module provides get-or-create and entry-append functions for parts
(3) and (4), following the same pattern as reply_helpers.py for parts
(1) and (2).
"""

from lxml import etree

from docx.document import Document
from docx.opc.part import XmlPart
from docx.oxml import parse_xml

W16CID_NS = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
W16CEX_NS = "http://schemas.microsoft.com/office/word/2018/wordml/cex"

COMMENTS_IDS_REL = (
    "http://schemas.microsoft.com/office/2016/09"
    "/relationships/commentsIds"
)
COMMENTS_IDS_CT = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.commentsIds+xml"
)
COMMENTS_EXTENSIBLE_REL = (
    "http://schemas.microsoft.com/office/2018/08"
    "/relationships/commentsExtensible"
)
COMMENTS_EXTENSIBLE_CT = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.commentsExtensible+xml"
)


def get_or_create_comments_ids_part(document: Document) -> XmlPart:
    """Get existing commentsIds OPC part or create a new one.

    Handles plain Part (no .element) by upgrading to XmlPart, same as
    reply_helpers does for commentsExtended.
    """
    for rel in document.part.rels.values():
        if rel.reltype == COMMENTS_IDS_REL:
            target = rel.target_part
            if not hasattr(target, "element"):
                return _upgrade_plain_part(document, target, COMMENTS_IDS_REL)
            return target
    return _create_ids_part(document)


def get_or_create_comments_extensible_part(document: Document) -> XmlPart:
    """Get existing commentsExtensible OPC part or create a new one.

    Handles plain Part (no .element) by upgrading to XmlPart.
    """
    for rel in document.part.rels.values():
        if rel.reltype == COMMENTS_EXTENSIBLE_REL:
            target = rel.target_part
            if not hasattr(target, "element"):
                return _upgrade_plain_part(
                    document, target, COMMENTS_EXTENSIBLE_REL,
                )
            return target
    return _create_extensible_part(document)


def add_comment_id_entry(ids_part: XmlPart, para_id: str, durable_id: str) -> None:
    """Append a w16cid:commentId entry to commentsIds.xml.

    Args:
        ids_part: The commentsIds.xml OPC part.
        para_id: The paraId of the comment paragraph.
        durable_id: A unique hex durableId for this comment.
    """
    nsmap = {"w16cid": W16CID_NS}
    entry = etree.SubElement(
        ids_part.element, f"{{{W16CID_NS}}}commentId", nsmap=nsmap,
    )
    entry.set(f"{{{W16CID_NS}}}paraId", para_id)
    entry.set(f"{{{W16CID_NS}}}durableId", durable_id)


def add_comment_extensible_entry(
    extensible_part: XmlPart, durable_id: str, date_utc: str,
) -> None:
    """Append a w16cex:commentExtensible entry to commentsExtensible.xml.

    Args:
        extensible_part: The commentsExtensible.xml OPC part.
        durable_id: Must match the durableId used in commentsIds.xml.
        date_utc: ISO 8601 UTC timestamp (e.g. "2026-03-07T12:00:00Z").
    """
    nsmap = {"w16cex": W16CEX_NS}
    entry = etree.SubElement(
        extensible_part.element,
        f"{{{W16CEX_NS}}}commentExtensible",
        nsmap=nsmap,
    )
    entry.set(f"{{{W16CEX_NS}}}durableId", durable_id)
    entry.set(f"{{{W16CEX_NS}}}dateUtc", date_utc)


def generate_durable_id(para_id: str) -> str:
    """Generate a deterministic durableId from a paraId.

    Uses a simple hash-based approach to produce an 8-character uppercase
    hex string that is unique per paraId. The durableId only needs to be
    unique within a single document.
    """
    hash_val = int(para_id, 16) ^ 0xA5A5A5A5
    return f"{hash_val & 0xFFFFFFFF:08X}"


def _upgrade_plain_part(document: Document, part, rel_type: str) -> XmlPart:
    """Upgrade a plain Part to XmlPart by re-creating with parsed blob."""
    root = etree.fromstring(part.blob)
    package = document.part.package
    xml_part = XmlPart(part.partname, part.content_type, root, package)
    if part in list(package.iter_parts()):
        package.parts.append(xml_part)
    for rel_key, rel in list(document.part.rels.items()):
        if rel.reltype == rel_type:
            document.part.rels[rel_key]._target = xml_part
            break
    return xml_part


def _create_ids_part(document: Document) -> XmlPart:
    """Create a fresh commentsIds.xml OPC part."""
    xml_str = (
        '<w16cid:commentsIds'
        ' xmlns:w16cid="http://schemas.microsoft.com/office/word/2016/wordml/cid"'
        '/>'
    )
    package = document.part.package
    partname = package.next_partname("/word/commentsIds%d.xml")
    root = parse_xml(xml_str.encode("utf-8"))
    ids_part = XmlPart(partname, COMMENTS_IDS_CT, root, package)
    package.parts.append(ids_part)
    document.part.relate_to(ids_part, COMMENTS_IDS_REL)
    return ids_part


def _create_extensible_part(document: Document) -> XmlPart:
    """Create a fresh commentsExtensible.xml OPC part."""
    xml_str = (
        '<w16cex:commentsExtensible'
        ' xmlns:w16cex="http://schemas.microsoft.com/office/word/2018/wordml/cex"'
        '/>'
    )
    package = document.part.package
    partname = package.next_partname("/word/commentsExtensible%d.xml")
    root = parse_xml(xml_str.encode("utf-8"))
    ext_part = XmlPart(partname, COMMENTS_EXTENSIBLE_CT, root, package)
    package.parts.append(ext_part)
    document.part.relate_to(ext_part, COMMENTS_EXTENSIBLE_REL)
    return ext_part
