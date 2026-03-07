"""CriticMarkup annotated text extraction from .docx documents.

Walks OOXML paragraph elements to detect tracked changes (w:ins,
w:del) and comment references, emitting CriticMarkup syntax with
author/date metadata. Handles nested counter-proposals (w:del inside
w:ins) and multi-round chained negotiations as sibling w:ins elements.

CriticMarkup output format:
    Insertion:  {++inserted text++}{>>[Ins] Author @ Date<<}
    Deletion:   {--deleted text--}{>>[Del] Author @ Date<<}
    Comment:    {>>comment text -- Author @ Date<<}
"""

from docx import Document
from docx.oxml.ns import qn

from adeu.utils.docx import get_paragraph_prefix, iter_document_parts

from src.ingestion.sdt_unwrapper import iter_effective_children
from src.ingestion.annotated_helpers import (
    process_insertion,
    process_run,
    process_top_level_deletion,
)
from src.ingestion.comment_loader import load_comments
from src.ingestion.validation import IngestionError, validate_docx_path


def extract_annotated_text(file_path: str) -> str:
    """Extract CriticMarkup-annotated text from a .docx document.

    Validates the file path, opens the document, loads comments, and
    walks all document parts (body, headers, footers) to produce
    annotated text with tracked change markers and author attribution.

    Args:
        file_path: String path to the .docx file.

    Returns:
        CriticMarkup-annotated text string. For clean documents (no
        tracked changes), returns plain text identical to clean extraction.

    Raises:
        IngestionError: If the file is invalid or extraction fails.
    """
    validated_path = validate_docx_path(file_path)

    try:
        document = Document(str(validated_path))
        comments_lookup = load_comments(document)
        return _build_annotated_output(document, comments_lookup)
    except IngestionError:
        raise
    except Exception as error:
        raise IngestionError(
            f"Failed to extract annotated text from {validated_path.name}: "
            f"{error}"
        ) from error


def _build_annotated_output(
    document: Document, comments_lookup: dict[str, dict]
) -> str:
    """Build the full annotated text output from all document parts.

    Iterates body, headers, and footers using Adeu's iter_document_parts
    helper. For each paragraph, applies heading prefix and annotated
    paragraph conversion.

    Args:
        document: A python-docx Document object.
        comments_lookup: Comment ID to metadata dict from load_comments.

    Returns:
        The complete annotated text string.
    """
    output_lines: list[str] = []

    for part in iter_document_parts(document):
        for paragraph in part.paragraphs:
            prefix = get_paragraph_prefix(paragraph)
            annotated_text = _annotate_paragraph(
                paragraph._element, comments_lookup
            )
            if annotated_text:
                output_lines.append(prefix + annotated_text)
            else:
                output_lines.append("")

    return "\n".join(output_lines)


def _annotate_paragraph(
    para_element, comments_lookup: dict[str, dict]
) -> str:
    """Convert a paragraph's XML children to CriticMarkup-annotated text.

    Dispatches on each direct child element's tag:
    - w:r (plain run): extracts text, checks for commentReference
    - w:ins (insertion): emits {++text++} with [Ins] metadata,
      handling nested w:del for counter-proposals
    - w:del (top-level deletion): emits {--text--} with [Del] metadata
    - w:commentRangeStart/End: skipped (markers only)
    - Other tags (w:pPr, bookmarks, etc.): skipped

    Args:
        para_element: An lxml element with tag w:p.
        comments_lookup: Comment ID to metadata dict.

    Returns:
        The annotated text for this paragraph.
    """
    parts: list[str] = []

    for child in iter_effective_children(para_element):
        tag = child.tag

        if tag == qn("w:r"):
            parts.append(process_run(child, comments_lookup))

        elif tag == qn("w:ins"):
            parts.append(process_insertion(child, comments_lookup))

        elif tag == qn("w:del"):
            parts.append(process_top_level_deletion(child))

        # w:commentRangeStart, w:commentRangeEnd, w:pPr, bookmarks,
        # and other elements are skipped silently.

    return "".join(parts)
