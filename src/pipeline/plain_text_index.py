"""PlainTextIndex -- formatting-marker-aware position mapping.

Builds a plain-text view of a DocumentMapper by stripping virtual spans
(formatting markers like ** and _, CriticMarkup wrappers, separators).
Only text from real spans (those backed by a w:r Run) is kept. A position
map translates match positions in plain_text back to the mapper's
full_text coordinates.

This class is the third fallback layer in three-layer matching:
1. Full mapper (includes all markers)
2. Clean mapper (strips CriticMarkup, keeps **/_ )
3. PlainTextIndex (strips ALL virtual spans including **/_ )

Ported from ~/vibe-legal-redliner/python/pipeline.py (lines 39-123).

Usage:
    from src.pipeline.plain_text_index import PlainTextIndex

    pti = PlainTextIndex(mapper)
    start, length = pti.find_match("target text")
    # start is in mapper.full_text coordinates
"""

import re


class PlainTextIndex:
    """Formatting-marker-aware position mapping for resilient matching.

    Iterates mapper.spans, keeping only spans where span.run is not None
    (real runs, not virtual/formatting spans). Builds a position map from
    plain-text indices to mapper full_text indices.

    Attributes:
        plain_text: Concatenated text from real spans only.
    """

    __slots__ = ("plain_text", "_plain_to_full")

    def __init__(self, mapper) -> None:
        """Build plain-text view from mapper, filtering virtual spans."""
        plain_chars: list[str] = []
        pos_map: list[int] = []

        for span in mapper.spans:
            if span.run is None:
                continue  # Virtual span -- skip
            for i, ch in enumerate(span.text):
                plain_chars.append(ch)
                pos_map.append(span.start + i)

        self.plain_text = "".join(plain_chars)
        self._plain_to_full = pos_map

    def find_match(self, target_text: str) -> tuple[int, int]:
        """Search plain_text for target_text with three fallback strategies.

        Strategies (mirroring DocumentMapper.find_match_index):
            1. Exact match
            2. Smart-quote normalization
            3. Fuzzy regex (flexible whitespace, underscores, quotes)

        Returns (full_text_start, full_text_length) or (-1, 0).
        Coordinates are in the mapper's full_text space, so they can be
        passed directly to find_target_runs_by_index().
        """
        idx = self._search(target_text)
        if idx == -1:
            return -1, 0
        return self._map_range(idx, len(target_text))

    def _search(self, target_text: str) -> int:
        """Return start index in plain_text, or -1."""
        # Strategy 1: Exact match
        idx = self.plain_text.find(target_text)
        if idx != -1:
            return idx

        # Strategy 2: Smart-quote normalization
        normalized_plain = _normalize_quotes(self.plain_text)
        normalized_target = _normalize_quotes(target_text)
        idx = normalized_plain.find(normalized_target)
        if idx != -1:
            return idx

        # Strategy 3: Fuzzy regex
        return _fuzzy_regex_search(self.plain_text, target_text)

    def _map_range(
        self, plain_start: int, plain_len: int,
    ) -> tuple[int, int]:
        """Convert (plain_start, plain_len) to (full_start, full_len)."""
        if not self._plain_to_full:
            return -1, 0
        full_start = self._plain_to_full[plain_start]
        end_idx = min(
            plain_start + plain_len - 1,
            len(self._plain_to_full) - 1,
        )
        full_end = self._plain_to_full[end_idx] + 1  # exclusive
        return full_start, full_end - full_start


def _normalize_quotes(text: str) -> str:
    """Replace smart/curly quotes with ASCII equivalents."""
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def _fuzzy_regex_search(text: str, target_text: str) -> int:
    """Build a fuzzy regex from target_text and search in text.

    Permits flexible whitespace, underscores, and quote variants.
    Returns start index or -1 on no match or regex error.
    """
    try:
        pattern = _make_fuzzy_regex(target_text)
        match = re.search(pattern, text)
        return match.start() if match else -1
    except re.error:
        return -1


def _make_fuzzy_regex(target_text: str) -> str:
    """Build a fuzzy regex permitting whitespace/quote/underscore variants.

    Mirrors DocumentMapper._make_fuzzy_regex from Adeu.
    """
    target_text = _normalize_quotes(target_text)
    parts: list[str] = []
    token_pattern = re.compile(r"(_+)|(\s+)|(['\"])")

    last = 0
    for match in token_pattern.finditer(target_text):
        literal = target_text[last : match.start()]
        if literal:
            parts.append(re.escape(literal))

        group_under, group_space, group_quote = match.groups()
        if group_under:
            parts.append(r"_+")
        elif group_space:
            parts.append(r"\s+")
        elif group_quote:
            parts.append(
                r"[''']" if group_quote == "'" else r'["""\u201c\u201d]',
            )
        last = match.end()

    tail = target_text[last:]
    if tail:
        parts.append(re.escape(tail))

    return "".join(parts)
