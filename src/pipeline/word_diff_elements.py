"""OOXML element builder for word-level diff segments.

Converts diff output [(op, text), ...] into lxml OxmlElement objects
ready for DOM insertion. Formatting preservation uses a character-level
format map built from the original target runs.

Ported from ~/vibe-legal-redliner/python/pipeline.py (lines 353-511).

Usage:
    from src.pipeline.word_diff_elements import (
        build_char_format_map, build_diff_elements,
    )
"""

from copy import deepcopy

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def build_char_format_map(target_runs, match_len: int) -> list:
    """Map each character position in target runs to its rPr element.

    Walks target runs character by character, recording the run's rPr
    for each position. Truncated to match_len.
    """
    char_map: list = []
    for run in target_runs:
        rpr = run._r.rPr  # python-docx CT_R.rPr property
        text = run.text or ""
        for _ in text:
            char_map.append(rpr)
    return char_map[:match_len] if match_len else char_map


def build_diff_elements(
    diffs: list[tuple[int, str]],
    char_format_map: list,
    engine,
    match_start_pos: int = 0,
) -> list:
    """Build OOXML elements from word-level diff segments.

    EQUAL -> plain w:r runs split at formatting boundaries.
    DELETE -> w:del > w:r > w:delText split at formatting boundaries.
    INSERT -> w:ins > w:r > w:t inheriting rPr from deletion position.
    """
    elements: list = []
    old_pos = match_start_pos
    ins_inherit_pos = match_start_pos

    for op, text in diffs:
        if not text:
            continue
        if op == 0:
            elements.extend(
                _build_equal_elements(text, char_format_map, old_pos),
            )
            old_pos += len(text)
            ins_inherit_pos = old_pos
        elif op == -1:
            ins_inherit_pos = old_pos
            elements.append(
                _build_delete_element(text, char_format_map, old_pos, engine),
            )
            old_pos += len(text)
        elif op == 1:
            elements.append(
                _build_insert_element(
                    text, char_format_map, ins_inherit_pos, engine,
                ),
            )
    return elements


def _build_equal_elements(text, char_format_map, start_pos):
    """Build plain w:r elements for EQUAL text, split at formatting boundaries."""
    segments = _split_by_formatting(text, start_pos, char_format_map)
    elements: list = []
    for seg_text, seg_rpr in segments:
        run = OxmlElement("w:r")
        if seg_rpr is not None:
            run.append(seg_rpr)
        t_elem = OxmlElement("w:t")
        t_elem.text = seg_text
        t_elem.set(qn("xml:space"), "preserve")
        run.append(t_elem)
        elements.append(run)
    return elements


def _build_delete_element(text, char_format_map, start_pos, engine):
    """Build w:del element wrapping deleted text runs."""
    del_tag = engine._create_track_change_tag("w:del")
    segments = _split_by_formatting(text, start_pos, char_format_map)
    for seg_text, seg_rpr in segments:
        run = OxmlElement("w:r")
        if seg_rpr is not None:
            run.append(seg_rpr)
        dt = OxmlElement("w:delText")
        dt.text = seg_text
        dt.set(qn("xml:space"), "preserve")
        run.append(dt)
        del_tag.append(run)
    return del_tag


def _build_insert_element(text, char_format_map, ins_inherit_pos, engine):
    """Build w:ins element with text inheriting rPr from deletion position."""
    ins_tag = engine._create_track_change_tag("w:ins")
    rpr = _get_rpr_at(char_format_map, ins_inherit_pos)
    run = OxmlElement("w:r")
    if rpr is not None:
        run.append(rpr)
    t_elem = OxmlElement("w:t")
    t_elem.text = text
    t_elem.set(qn("xml:space"), "preserve")
    run.append(t_elem)
    ins_tag.append(run)
    return ins_tag


def _get_rpr_at(char_format_map: list, char_pos: int):
    """Get a deep copy of the rPr at char_pos, or None if no formatting."""
    if not char_format_map:
        return None
    pos = max(0, min(char_pos, len(char_format_map) - 1))
    if char_format_map[pos] is not None:
        return deepcopy(char_format_map[pos])
    return None


def _split_by_formatting(text, start_pos, char_format_map):
    """Split text into (text, rPr) segments at formatting boundaries.

    Compares original rPr references from char_format_map to detect
    where formatting changes. Returns deep-copied rPr in each segment.
    """
    if not text:
        return []

    segments: list[tuple[str, object]] = []
    seg_text = ""
    seg_rpr = None
    started = False

    for i, char in enumerate(text):
        pos = start_pos + i
        clamped = max(0, min(pos, len(char_format_map) - 1)) if char_format_map else 0
        rpr = char_format_map[clamped] if char_format_map else None

        if not started:
            seg_text = char
            seg_rpr = rpr
            started = True
        elif _rpr_equal(seg_rpr, rpr):
            seg_text += char
        else:
            segments.append(
                (seg_text, deepcopy(seg_rpr) if seg_rpr is not None else None),
            )
            seg_text = char
            seg_rpr = rpr

    if seg_text:
        segments.append(
            (seg_text, deepcopy(seg_rpr) if seg_rpr is not None else None),
        )
    return segments


def _rpr_equal(rpr1, rpr2) -> bool:
    """Compare two rPr elements for formatting equality."""
    if rpr1 is None and rpr2 is None:
        return True
    if rpr1 is None or rpr2 is None:
        return False
    if rpr1 is rpr2:
        return True
    for tag in ["w:b", "w:i", "w:u"]:
        if (rpr1.find(qn(tag)) is not None) != (rpr2.find(qn(tag)) is not None):
            return False
    return True
