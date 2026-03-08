"""OOXML element construction helpers for anchor module operations.

Self-contained OOXML helpers for tracked-change element creation,
counter-proposal layering, and run splitting. Extracted from anchor.py
to keep that module under 200 lines.
"""

from copy import deepcopy
from typing import Optional

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.run import Run
from lxml import etree


def get_insertion_text(ins_element: etree._Element) -> str:
    """Extract visible text from a w:ins element's direct w:r children."""
    text_parts = []
    for run in ins_element.findall(qn("w:r")):
        for text_elem in run.findall(qn("w:t")):
            text_parts.append(text_elem.text or "")
    return "".join(text_parts)


def get_max_revision_id(body: etree._Element) -> int:
    """Scan body for the highest w:id value across w:ins and w:del elements."""
    max_id = 0
    for element in body.iter():
        if element.tag in (qn("w:ins"), qn("w:del")):
            raw_id = element.get(qn("w:id"))
            if raw_id is not None and raw_id.isdigit():
                max_id = max(max_id, int(raw_id))
    return max_id


def create_tracked_change(
    tag: str, author: str, timestamp: str, revision_id: int,
) -> etree._Element:
    """Create a w:ins or w:del element with author, date, and id attributes."""
    element = OxmlElement(tag)
    element.set(qn("w:id"), str(revision_id))
    element.set(qn("w:author"), author)
    element.set(qn("w:date"), timestamp)
    return element


def create_run_with_text(
    text: str, source_rPr: Optional[etree._Element] = None,
) -> etree._Element:
    """Create a w:r with w:t child. Clones source_rPr for formatting."""
    run = OxmlElement("w:r")
    if source_rPr is not None:
        run.append(deepcopy(source_rPr))
    text_element = OxmlElement("w:t")
    text_element.set(qn("xml:space"), "preserve")
    text_element.text = text
    run.append(text_element)
    return run


def convert_run_text_to_del_text(run: etree._Element) -> None:
    """Convert all w:t elements in a run to w:delText."""
    for text_element in run.findall(qn("w:t")):
        text_element.tag = qn("w:delText")
        text_element.set(qn("xml:space"), "preserve")


def apply_clean_text_edit(
    target_runs: list[Run],
    new_text: str,
    author: str,
    timestamp: str,
    next_id: int,
) -> int:
    """Apply standard tracked change (w:del + w:ins) to clean text runs."""
    last_del_element = None
    source_rPr = None

    for run in target_runs:
        if source_rPr is None:
            source_rPr = run._element.find(qn("w:rPr"))
        del_tag = create_tracked_change("w:del", author, timestamp, next_id)
        next_id += 1
        copied_run = deepcopy(run._element)
        convert_run_text_to_del_text(copied_run)
        del_tag.append(copied_run)
        parent = run._element.getparent()
        parent.replace(run._element, del_tag)
        last_del_element = del_tag

    if new_text and last_del_element is not None:
        next_id = _insert_replacement_after(
            last_del_element, new_text, author, timestamp, next_id, source_rPr,
        )
    return next_id


def _insert_replacement_after(
    anchor_element: etree._Element,
    text: str,
    author: str,
    timestamp: str,
    next_id: int,
    source_rPr: Optional[etree._Element],
) -> int:
    """Insert a w:ins with replacement text as sibling after anchor_element."""
    ins_tag = create_tracked_change("w:ins", author, timestamp, next_id)
    next_id += 1
    new_run = create_run_with_text(text, source_rPr=source_rPr)
    ins_tag.append(new_run)
    parent = anchor_element.getparent()
    anchor_index = list(parent).index(anchor_element)
    parent.insert(anchor_index + 1, ins_tag)
    return next_id


def _counter_propose_full_insertion(
    ins_element: etree._Element,
    author: str,
    timestamp: str,
    replacement_text: str,
    next_id: int,
) -> int:
    """Counter-propose entire insertion: wrap all runs in w:del, add sibling w:ins."""
    direct_runs = ins_element.findall(qn("w:r"))
    source_rPr = None
    if direct_runs:
        source_rPr = direct_runs[0].find(qn("w:rPr"))

    for run in direct_runs:
        del_element = create_tracked_change("w:del", author, timestamp, next_id)
        next_id += 1
        copied_run = deepcopy(run)
        convert_run_text_to_del_text(copied_run)
        ins_element.remove(run)
        del_element.append(copied_run)
        ins_element.append(del_element)

    if replacement_text:
        next_id = _insert_replacement_after(
            ins_element, replacement_text, author, timestamp, next_id, source_rPr,
        )
    return next_id


def _counter_propose_partial_insertion(
    ins_element: etree._Element,
    target_text: str,
    replacement_text: str,
    author: str,
    timestamp: str,
    next_id: int,
) -> int:
    """Counter-propose a substring of an insertion via run splitting."""
    target_runs, source_rPr = _split_and_isolate_target(
        ins_element, target_text,
    )
    for run in target_runs:
        del_element = create_tracked_change("w:del", author, timestamp, next_id)
        next_id += 1
        copied_run = deepcopy(run)
        convert_run_text_to_del_text(copied_run)
        run.addnext(del_element)
        ins_element.remove(run)
        del_element.append(copied_run)

    if replacement_text:
        next_id = _insert_replacement_after(
            ins_element, replacement_text, author, timestamp, next_id, source_rPr,
        )
    return next_id


def apply_mixed_context_edit(
    anchor_map,
    start_idx: int,
    end_idx: int,
    new_text: str,
    author: str,
    timestamp: str,
    next_id: int,
) -> int:
    """Apply an edit spanning both insertion and clean text boundaries.

    Splits the operation so insertion portions get counter-proposed
    (w:del inside w:ins) and clean text portions get standard w:del,
    then places a single replacement w:ins after all deletions.
    """
    spans = anchor_map.resolve_spans(start_idx, end_idx)
    source_rPr = _extract_source_formatting(spans)
    last_element = None

    for span in spans:
        if span.ins_id is not None and span.wrapper_element is not None:
            next_id, last_element = _delete_insertion_span(
                span, author, timestamp, next_id,
            )
        elif span.run is not None:
            next_id, last_element = _delete_clean_span(
                span, start_idx, end_idx, author, timestamp, next_id,
            )

    if new_text and last_element is not None:
        next_id = _insert_replacement_after(
            last_element, new_text, author, timestamp, next_id, source_rPr,
        )
    return next_id


def _extract_source_formatting(spans: list) -> Optional[etree._Element]:
    """Extract w:rPr formatting from the first span with a run."""
    for span in spans:
        if span.run is not None:
            rPr = span.run._element.find(qn("w:rPr"))
            if rPr is not None:
                return rPr
    return None


def _delete_insertion_span(
    span,
    author: str,
    timestamp: str,
    next_id: int,
) -> tuple[int, etree._Element]:
    """Counter-propose the insertion portion of a mixed edit."""
    wrapper = span.wrapper_element
    full_ins_text = get_insertion_text(wrapper)

    ins_covered_text = span.text
    if ins_covered_text == full_ins_text:
        next_id = _counter_propose_full_insertion(
            wrapper, author, timestamp, "", next_id,
        )
    else:
        next_id = _counter_propose_partial_insertion(
            wrapper, ins_covered_text, "", author, timestamp, next_id,
        )
    return next_id, wrapper


def _delete_clean_span(
    span,
    edit_start: int,
    edit_end: int,
    author: str,
    timestamp: str,
    next_id: int,
) -> tuple[int, etree._Element]:
    """Wrap the targeted portion of a clean text run in a w:del."""
    run_element = span.run._element
    run_element = _split_clean_run_to_edit_boundary(
        run_element, span, edit_start, edit_end,
    )
    del_tag = create_tracked_change("w:del", author, timestamp, next_id)
    next_id += 1
    copied_run = deepcopy(run_element)
    convert_run_text_to_del_text(copied_run)
    del_tag.append(copied_run)
    parent = run_element.getparent()
    parent.replace(run_element, del_tag)
    return next_id, del_tag


def _split_clean_run_to_edit_boundary(
    run_element: etree._Element,
    span,
    edit_start: int,
    edit_end: int,
) -> etree._Element:
    """Split a clean run so the returned element covers only the edit range."""
    if span.clean_start < edit_start:
        split_at = edit_start - span.clean_start
        _split_run_element(run_element, split_at)
        run_element = run_element.getnext()

    if span.clean_end > edit_end:
        target_len = edit_end - max(span.clean_start, edit_start)
        _split_run_element(run_element, target_len)

    return run_element


def _split_and_isolate_target(
    ins_element: etree._Element, target_text: str,
) -> tuple[list[etree._Element], Optional[etree._Element]]:
    """Split runs inside a w:ins to isolate the target text substring."""
    direct_runs = ins_element.findall(qn("w:r"))
    source_rPr = direct_runs[0].find(qn("w:rPr")) if direct_runs else None

    run_map = _build_run_text_map(direct_runs)
    full_text = "".join(rt for _, rt, _ in run_map)
    target_start = full_text.find(target_text)
    if target_start == -1:
        return [], source_rPr
    target_end = target_start + len(target_text)

    return _collect_target_runs(run_map, target_start, target_end), source_rPr


def _build_run_text_map(
    runs: list[etree._Element],
) -> list[tuple[etree._Element, str, int]]:
    """Build [(run_element, text, cumulative_offset)] from direct runs."""
    run_map = []
    offset = 0
    for run in runs:
        text_elements = run.findall(qn("w:t"))
        run_text = "".join(t.text or "" for t in text_elements)
        run_map.append((run, run_text, offset))
        offset += len(run_text)
    return run_map


def _collect_target_runs(
    run_map: list[tuple[etree._Element, str, int]],
    target_start: int,
    target_end: int,
) -> list[etree._Element]:
    """Collect and split runs to isolate exactly [target_start, target_end)."""
    target_runs = []
    for run, run_text, run_offset in run_map:
        run_end = run_offset + len(run_text)
        if run_end <= target_start or run_offset >= target_end:
            continue

        if run_offset < target_start:
            local_split = target_start - run_offset
            _split_run_element(run, local_split)
            run = run.getnext()
            run_text = run_text[local_split:]
            run_offset = target_start
            run_end = run_offset + len(run_text)
            target_runs.append(run)
        elif run not in target_runs:
            target_runs.append(run)

        if run_end > target_end:
            local_split = target_end - run_offset
            _split_run_element(run, local_split)
    return target_runs


def _split_run_element(
    run_element: etree._Element, split_index: int,
) -> tuple[etree._Element, etree._Element]:
    """Split a w:r element at character index; inserts right sibling after."""
    text_elem = run_element.find(qn("w:t"))
    if text_elem is None:
        return run_element, run_element

    full_text = text_elem.text or ""
    left_text = full_text[:split_index]
    right_text = full_text[split_index:]

    text_elem.text = left_text
    if left_text != left_text.strip() or " " in left_text:
        text_elem.set(qn("xml:space"), "preserve")

    new_run = deepcopy(run_element)
    for t in new_run.findall(qn("w:t")):
        new_run.remove(t)
    new_t = OxmlElement("w:t")
    new_t.text = right_text
    if right_text != right_text.strip() or " " in right_text:
        new_t.set(qn("xml:space"), "preserve")
    new_run.append(new_t)

    run_element.addnext(new_run)
    return run_element, new_run
