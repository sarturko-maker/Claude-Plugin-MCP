"""OOXML manipulation helpers for counter-proposal operations.

Provides low-level functions to counter-propose insertions and deletions
by layering client-attributed tracked changes on top of counterparty
markup. Also provides get_max_revision_id for allocating unique OOXML
w:id values.

The OOXML patterns implemented here were validated in Phase 1:
- Counter-proposing insertion: nest w:del inside w:ins, add sibling w:ins
- Counter-proposing deletion: add w:ins after w:del (at correct nesting level)
"""

from copy import deepcopy

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree


def get_max_revision_id(body: etree._Element) -> int:
    """Scan all w:ins and w:del elements for the highest w:id value.

    Used to allocate unique IDs for new tracked change elements.
    Returns 0 if no tracked change elements are found.

    Args:
        body: The document body element to search.

    Returns:
        The highest w:id value found, or 0 if none exist.
    """
    max_id = 0
    for element in body.iter():
        if element.tag in (qn("w:ins"), qn("w:del")):
            raw_id = element.get(qn("w:id"))
            if raw_id is not None and raw_id.isdigit():
                max_id = max(max_id, int(raw_id))
    return max_id


def counter_propose_insertion(
    ins_element: etree._Element,
    client_author: str,
    timestamp: str,
    replacement_text: str,
    next_id: int,
) -> int:
    """Counter-propose an insertion by nesting w:del inside and adding sibling w:ins.

    Wraps each direct w:r child of the w:ins in a client-attributed w:del,
    converting w:t to w:delText. If replacement_text is non-empty, creates
    a new sibling w:ins with the client's replacement text.

    Args:
        ins_element: The counterparty's w:ins element to counter-propose.
        client_author: Author name for the client's tracked changes.
        timestamp: ISO 8601 timestamp for the client's changes.
        replacement_text: Client's proposed alternative (empty = reject only).
        next_id: Starting w:id for new elements.

    Returns:
        The next available w:id after all allocations.
    """
    # Collect direct w:r children (not runs inside nested w:del)
    direct_runs = ins_element.findall(qn("w:r"))

    # Capture source formatting from first run for replacement text
    source_rPr = None
    if direct_runs:
        source_rPr = direct_runs[0].find(qn("w:rPr"))

    for run in direct_runs:
        # Create w:del wrapper with client attribution
        del_element = _create_tracked_change("w:del", client_author, timestamp, next_id)
        next_id += 1

        # Deep copy the run and convert w:t to w:delText
        copied_run = deepcopy(run)
        _convert_run_text_to_del_text(copied_run)

        # Remove original run first, then append the w:del with copied run
        ins_element.remove(run)
        del_element.append(copied_run)
        ins_element.append(del_element)

    # If replacement text provided, add sibling w:ins after the original
    if replacement_text:
        new_ins = _create_tracked_change("w:ins", client_author, timestamp, next_id)
        next_id += 1
        new_run = _create_run_with_text(replacement_text, source_rPr=source_rPr)
        new_ins.append(new_run)

        parent = ins_element.getparent()
        ins_index = list(parent).index(ins_element)
        parent.insert(ins_index + 1, new_ins)

    return next_id


def counter_propose_deletion(
    del_element: etree._Element,
    client_author: str,
    timestamp: str,
    replacement_text: str,
    next_id: int,
) -> int:
    """Counter-propose a deletion by adding w:ins with replacement text.

    Places a client-attributed w:ins adjacent to the counterparty's w:del
    at the correct nesting level. If the w:del is inside a w:ins wrapper,
    the new w:ins goes after the wrapper in the paragraph.

    Args:
        del_element: The counterparty's w:del element to counter-propose.
        client_author: Author name for the client's tracked changes.
        timestamp: ISO 8601 timestamp for the client's changes.
        replacement_text: Client's proposed alternative text.
        next_id: Starting w:id for new elements.

    Returns:
        The next available w:id after all allocations.
    """
    # Extract source formatting from deleted runs for replacement text
    del_runs = del_element.findall(qn("w:r"))
    source_rPr = None
    if del_runs:
        source_rPr = del_runs[0].find(qn("w:rPr"))

    new_ins = _create_tracked_change("w:ins", client_author, timestamp, next_id)
    next_id += 1
    new_run = _create_run_with_text(replacement_text, source_rPr=source_rPr)
    new_ins.append(new_run)

    # Determine correct insertion point based on nesting
    parent = del_element.getparent()
    if parent.tag == qn("w:ins"):
        # w:del is inside a w:ins wrapper; place new w:ins after the wrapper
        grandparent = parent.getparent()
        wrapper_index = list(grandparent).index(parent)
        grandparent.insert(wrapper_index + 1, new_ins)
    else:
        # w:del is directly in the paragraph; place new w:ins after it
        del_index = list(parent).index(del_element)
        parent.insert(del_index + 1, new_ins)

    return next_id


def _create_tracked_change(
    tag: str, author: str, timestamp: str, revision_id: int
) -> etree._Element:
    """Create a w:ins or w:del element with author, date, and id attributes."""
    element = OxmlElement(tag)
    element.set(qn("w:id"), str(revision_id))
    element.set(qn("w:author"), author)
    element.set(qn("w:date"), timestamp)
    return element


def _create_run_with_text(
    text: str,
    source_rPr: etree._Element | None = None,
) -> etree._Element:
    """Create a w:r element containing a w:t with the given text.

    Sets xml:space='preserve' on the w:t to ensure whitespace is retained.
    If source_rPr is provided, clones it into the run so that replacement
    text inherits the original formatting (bold, italic, font, etc.).

    Args:
        text: The text content for the run.
        source_rPr: Optional w:rPr element to clone for formatting preservation.

    Returns:
        A new w:r element with a w:t child (and optional w:rPr).
    """
    run = OxmlElement("w:r")
    if source_rPr is not None:
        run.append(deepcopy(source_rPr))
    text_element = OxmlElement("w:t")
    text_element.set(qn("xml:space"), "preserve")
    text_element.text = text
    run.append(text_element)
    return run


def _convert_run_text_to_del_text(run: etree._Element) -> None:
    """Convert all w:t elements in a run to w:delText for use inside w:del."""
    for text_element in run.findall(qn("w:t")):
        text_element.tag = qn("w:delText")
        text_element.set(qn("xml:space"), "preserve")
