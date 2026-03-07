"""Helper functions for CriticMarkup annotated text extraction.

Contains the low-level element processing functions that convert
individual OOXML elements (w:r, w:ins, w:del) into CriticMarkup
syntax. Used by annotated_extractor.py's paragraph walker.
"""

from docx.oxml.ns import qn

from src.ingestion.sdt_unwrapper import iter_effective_children


def process_run(
    run_element, comments_lookup: dict[str, dict]
) -> str:
    """Extract text from a plain w:r element, handling comment references.

    Checks if the run contains a w:commentReference. If so, looks up
    the comment in the comments lookup and emits CriticMarkup comment
    syntax. Otherwise, extracts regular text from w:t elements.

    Args:
        run_element: An lxml element with tag w:r.
        comments_lookup: Comment ID to metadata dict.

    Returns:
        Plain text or CriticMarkup comment marker.
    """
    comment_ref = run_element.find(qn("w:commentReference"))
    if comment_ref is not None:
        comment_id = comment_ref.get(qn("w:id"))
        if comment_id and comment_id in comments_lookup:
            comment = comments_lookup[comment_id]
            return (
                f"{{>>{comment['text']} -- "
                f"{comment['author']} @ {comment['date']}<<}}"
            )
        return ""

    return extract_run_text(run_element)


def process_insertion(
    ins_element, comments_lookup: dict[str, dict]
) -> str:
    """Process a w:ins element, handling nested w:del for counter-proposals.

    For each child of the insertion:
    - w:del (nested deletion = counter-proposal): emits deletion markers
      with the del author's attribution
    - w:r (inserted run): accumulates text, then emits insertion markers
      with the ins author's attribution

    Args:
        ins_element: An lxml element with tag w:ins.
        comments_lookup: Comment ID to metadata dict.

    Returns:
        CriticMarkup insertion/deletion markers with metadata.
    """
    author = ins_element.get(qn("w:author")) or ""
    date = ins_element.get(qn("w:date")) or ""
    parts: list[str] = []
    inserted_text_parts: list[str] = []

    for child in iter_effective_children(ins_element):
        child_tag = child.tag

        if child_tag == qn("w:del"):
            _flush_insertion_text(inserted_text_parts, author, date, parts)
            del_author = child.get(qn("w:author")) or ""
            del_date = child.get(qn("w:date")) or ""
            del_text = extract_del_text(child)
            parts.append(f"{{--{del_text}--}}")
            parts.append(f"{{>>[Del] {del_author} @ {del_date}<<}}")

        elif child_tag == qn("w:r"):
            comment_ref = child.find(qn("w:commentReference"))
            if comment_ref is not None:
                _flush_insertion_text(
                    inserted_text_parts, author, date, parts
                )
                comment_id = comment_ref.get(qn("w:id"))
                if comment_id and comment_id in comments_lookup:
                    comment = comments_lookup[comment_id]
                    parts.append(
                        f"{{>>{comment['text']} -- "
                        f"{comment['author']} @ {comment['date']}<<}}"
                    )
            else:
                inserted_text_parts.append(extract_run_text(child))

        # Skip w:rPr, w:bookmarkStart, w:bookmarkEnd, etc.

    _flush_insertion_text(inserted_text_parts, author, date, parts)
    return "".join(parts)


def process_top_level_deletion(del_element) -> str:
    """Process a top-level w:del element (not nested inside w:ins).

    Extracts deleted text from w:delText elements and emits CriticMarkup
    deletion markers with author/date metadata.

    Args:
        del_element: An lxml element with tag w:del.

    Returns:
        CriticMarkup deletion marker with [Del] metadata.
    """
    author = del_element.get(qn("w:author")) or ""
    date = del_element.get(qn("w:date")) or ""
    del_text = extract_del_text(del_element)
    return f"{{--{del_text}--}}{{>>[Del] {author} @ {date}<<}}"


def extract_run_text(run_element) -> str:
    """Extract text from a w:r element's w:t children.

    Handles w:t, w:tab (as space), and w:br (as newline), matching
    the behavior of Adeu's get_run_text but working with raw lxml
    elements instead of python-docx Run objects.

    Args:
        run_element: An lxml element with tag w:r.

    Returns:
        The extracted text content of the run.
    """
    text_parts: list[str] = []
    for child in run_element:
        if child.tag == qn("w:t"):
            text_parts.append(child.text or "")
        elif child.tag == qn("w:tab"):
            text_parts.append(" ")
        elif child.tag in (qn("w:br"), qn("w:cr")):
            text_parts.append("\n")
    return "".join(text_parts)


def extract_del_text(del_element) -> str:
    """Extract deleted text from a w:del element's w:delText children.

    Walks runs inside a w:del element and reads w:delText elements.
    Does NOT use w:t -- deleted text uses w:delText in OOXML.

    Args:
        del_element: An lxml element with tag w:del.

    Returns:
        The combined deleted text content.
    """
    text_parts: list[str] = []
    for run in del_element.findall(qn("w:r")):
        for del_text_element in run.findall(qn("w:delText")):
            if del_text_element.text:
                text_parts.append(del_text_element.text)
    return "".join(text_parts)


def _flush_insertion_text(
    text_parts: list[str],
    author: str,
    date: str,
    output: list[str],
) -> None:
    """Emit accumulated insertion text as a CriticMarkup insertion marker.

    Joins accumulated run text parts, wraps in {++ ++} markers, and
    appends [Ins] metadata. Clears the text_parts list afterward.

    Args:
        text_parts: List of accumulated text strings from inserted runs.
        author: The w:author attribute of the parent w:ins element.
        date: The w:date attribute of the parent w:ins element.
        output: The output parts list to append to.
    """
    if text_parts:
        joined_text = "".join(text_parts)
        if joined_text:
            output.append(f"{{++{joined_text}++}}")
            output.append(f"{{>>[Ins] {author} @ {date}<<}}")
        text_parts.clear()
