"""Post-save OOXML validation for .docx files.

Checks structural integrity of a .docx file (which is a ZIP archive
containing XML parts). Catches issues that would trigger Word's repair
dialog: malformed XML, missing required parts, orphaned content type
references.

Never raises exceptions -- always returns a list of warning strings.
Empty list means the file is structurally valid.

Usage:
    from src.validation.output_validator import validate_docx_output

    warnings = validate_docx_output("output/result.docx")
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
"""

import zipfile
from pathlib import Path

from lxml import etree


CONTENT_TYPES_NS = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)


def validate_docx_output(file_path: str) -> list[str]:
    """Validate structural integrity of a .docx file.

    Checks:
        1. File is a valid ZIP archive
        2. Required OOXML parts exist ([Content_Types].xml, _rels/.rels)
        3. All .xml and .rels files contain well-formed XML
        4. All Override PartName references in [Content_Types].xml exist

    Args:
        file_path: Path to the .docx file to validate.

    Returns:
        List of warning strings. Empty list means valid.
    """
    warnings: list[str] = []

    if not zipfile.is_zipfile(file_path):
        warnings.append(f"{Path(file_path).name} is not a valid ZIP file")
        return warnings

    with zipfile.ZipFile(file_path, "r") as zf:
        _check_required_parts(zf, warnings)
        _check_xml_wellformedness(zf, warnings)
        _check_orphaned_content_types(zf, warnings)

    return warnings


def _check_required_parts(
    zf: zipfile.ZipFile, warnings: list[str]
) -> None:
    """Check that required OOXML parts exist in the archive."""
    names = zf.namelist()
    if "[Content_Types].xml" not in names:
        warnings.append("Missing required part: [Content_Types].xml")
    if "_rels/.rels" not in names:
        warnings.append("Missing required part: _rels/.rels")


def _check_xml_wellformedness(
    zf: zipfile.ZipFile, warnings: list[str]
) -> None:
    """Check that all .xml and .rels files contain well-formed XML."""
    for name in zf.namelist():
        if not (name.endswith(".xml") or name.endswith(".rels")):
            continue
        try:
            data = zf.read(name)
            etree.fromstring(data)
        except etree.XMLSyntaxError:
            warnings.append(f"Malformed XML in {name}")


def _check_orphaned_content_types(
    zf: zipfile.ZipFile, warnings: list[str]
) -> None:
    """Check that Override PartName references point to existing parts."""
    if "[Content_Types].xml" not in zf.namelist():
        return

    try:
        data = zf.read("[Content_Types].xml")
        root = etree.fromstring(data)
    except etree.XMLSyntaxError:
        return  # Already reported by wellformedness check

    zip_names = set(zf.namelist())

    for override in root.findall(
        f"{{{CONTENT_TYPES_NS}}}Override"
    ):
        part_name = override.get("PartName", "")
        # PartName starts with '/' -- strip leading slash for zip lookup
        normalized = part_name.lstrip("/")
        if normalized and normalized not in zip_names:
            warnings.append(
                f"Content type references missing part: {part_name}"
            )
