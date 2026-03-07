"""Word-level diff engine using diff-match-patch with token encoding.

Tokenizes text with r'\\S+|\\s+' so punctuation stays attached to words
(legal standard: "claims." is one token, not "claims" + "."). Whitespace
sequences become separate tokens. Tokens are encoded to unique Unicode
characters, diffed via diff_match_patch, then decoded back to produce
word-granularity segments.

This module is ported from ~/vibe-legal-redliner/python/pipeline.py
(lines 306-351) and adapted for the Claude-Plugin project structure.

Usage:
    from src.pipeline.word_diff import diff_words, verify_reconstruction

    diffs = diff_words("within thirty days", "within fourteen days")
    # [(0, "within "), (-1, "thirty"), (1, "fourteen"), (0, " days")]

    ok = verify_reconstruction(diffs, "within fourteen days")
    # True
"""

import re

from diff_match_patch import diff_match_patch


def diff_words(
    old_text: str,
    new_text: str,
) -> list[tuple[int, str]]:
    """Produce word-level diff segments between old_text and new_text.

    Uses token encoding: each word or whitespace chunk maps to a unique
    Unicode character (starting at U+0100). diff_match_patch operates on
    the encoded strings, then results are decoded back to word-level text.

    Returns a list of (op, text) tuples where:
        op = -1: DELETE (text present in old, absent in new)
        op =  0: EQUAL  (text unchanged)
        op =  1: INSERT (text absent in old, present in new)
    """
    token_regex = re.compile(r"\S+|\s+")
    old_tokens = token_regex.findall(old_text) if old_text else []
    new_tokens = token_regex.findall(new_text) if new_text else []

    if not old_tokens and not new_tokens:
        return []

    encoded_old, encoded_new, char_to_token = _encode_tokens(
        old_tokens, new_tokens,
    )

    dmp = diff_match_patch()
    diffs = dmp.diff_main(encoded_old, encoded_new)
    dmp.diff_cleanupSemantic(diffs)

    return _decode_diffs(diffs, char_to_token)


def verify_reconstruction(
    diffs: list[tuple[int, str]],
    expected_new_text: str,
) -> bool:
    """Check whether INSERT + EQUAL segments reassemble to expected text.

    Joins all text from segments where op >= 0 (EQUAL and INSERT) and
    compares to expected_new_text. Returns True if they match exactly.
    This is the reconstruction safety check: a mismatch means the diff
    would produce incorrect document text if applied.
    """
    reconstructed = "".join(text for op, text in diffs if op >= 0)
    return reconstructed == expected_new_text


def _encode_tokens(
    old_tokens: list[str],
    new_tokens: list[str],
) -> tuple[str, str, dict[str, str]]:
    """Map word/whitespace tokens to unique Unicode characters.

    Returns (encoded_old, encoded_new, char_to_token) where
    char_to_token maps each Unicode character back to its original token.
    """
    token_to_char: dict[str, str] = {}
    char_to_token: dict[str, str] = {}
    next_code = 0x100  # Start above ASCII range

    def encode(tokens: list[str]) -> str:
        """Encode a list of text tokens into single-character representations for diff comparison."""
        nonlocal next_code
        chars: list[str] = []
        for token in tokens:
            if token not in token_to_char:
                char = chr(next_code)
                token_to_char[token] = char
                char_to_token[char] = token
                next_code += 1
            chars.append(token_to_char[token])
        return "".join(chars)

    return encode(old_tokens), encode(new_tokens), char_to_token


def _decode_diffs(
    diffs: list[tuple[int, str]],
    char_to_token: dict[str, str],
) -> list[tuple[int, str]]:
    """Decode encoded diff output back to word-level text segments."""
    result: list[tuple[int, str]] = []
    for op, encoded_text in diffs:
        decoded = "".join(char_to_token[c] for c in encoded_text)
        if decoded:
            result.append((op, decoded))
    return result
