"""In-memory counter-propose operation for the atomic pipeline.

Layers client-attributed tracked changes on a pre-loaded Document object
without any file I/O. The caller provides a Document, pre-resolved
(TrackedChangeEntry, replacement_text) pairs, and an AuthorConfig.
This module does NOT call build_state_of_play(), Document(path), or .save().

Routes through surgical word-level diff when the tracked change element
is simple (single w:r child) and the diff reconstructs cleanly. Falls
back to wholesale counter_propose_insertion/deletion for complex cases.
Includes a validation gate: after computing diffs, verifies the accepted-view
matches the intended replacement before applying surgical changes.
Returns ActionOutcome records compatible with the pipeline result model.
"""

import logging

from docx.document import Document

logger = logging.getLogger(__name__)

from src.models.author_config import AuthorConfig
from src.models.change import TrackedChangeEntry
from src.negotiation.accept_helpers import find_tracked_change_element
from src.negotiation.counter_propose_helpers import (
    counter_propose_deletion,
    counter_propose_insertion,
    get_max_revision_id,
)
from src.negotiation.counter_propose_surgical import (
    apply_surgical_deletion_counter_propose,
    apply_surgical_insertion_counter_propose,
    can_apply_surgical_diff,
    compute_surgical_diffs,
    extract_element_text,
    is_text_identical,
)
from src.negotiation.timestamp import generate_timestamp
from src.pipeline.results import ActionOutcome


def counter_propose_on_document(
    document: Document,
    resolutions: list[tuple[TrackedChangeEntry, str]],
    author_config: AuthorConfig,
) -> list[ActionOutcome]:
    """Counter-propose tracked changes on an in-memory Document.

    For each (entry, replacement_text) pair, finds the tracked change
    element by ooxml_id and applies the appropriate counter-proposal.
    Uses word-level surgical diff for simple single-run elements,
    falling back to wholesale replacement for complex cases.

    Args:
        document: A pre-loaded python-docx Document object.
        resolutions: List of (TrackedChangeEntry, replacement_text) tuples.
        author_config: Client author configuration for attribution.

    Returns:
        List of ActionOutcome records with status for each counter-proposal.
    """
    body = document.element.body
    next_id = get_max_revision_id(body) + 1
    timestamp = generate_timestamp(author_config.date_override)
    client_author = author_config.name
    outcomes: list[ActionOutcome] = []

    for entry, replacement_text in resolutions:
        outcome, next_id = _counter_propose_single(
            body, entry, replacement_text, client_author, timestamp, next_id
        )
        outcomes.append(outcome)

    return outcomes


def _counter_propose_single(
    body,
    entry: TrackedChangeEntry,
    replacement_text: str,
    client_author: str,
    timestamp: str,
    next_id: int,
) -> tuple[ActionOutcome, int]:
    """Process a single counter-proposal with surgical or wholesale routing.

    Attempts surgical word-level diff first for simple elements. Falls
    back to wholesale counter_propose_insertion/deletion for complex
    elements or when diff reconstruction fails.

    Returns:
        Tuple of (ActionOutcome, next_id).
    """
    element = find_tracked_change_element(body, entry.ooxml_id)
    if element is None:
        return ActionOutcome(
            action_type="counter_propose",
            target_id=entry.change_id,
            status="failed",
            reason=f"XML element not found for ooxml_id={entry.ooxml_id}",
            original_text=entry.changed_text,
        ), next_id

    # Extract text from the element to check for no-change
    element_text = extract_element_text(element, entry.change_type)
    if is_text_identical(element_text, replacement_text):
        return ActionOutcome(
            action_type="counter_propose",
            target_id=entry.change_id,
            status="skipped",
            reason="Replacement text identical to original",
            original_text=entry.changed_text,
            new_text=replacement_text,
        ), next_id

    # Try surgical path for simple single-run elements
    if can_apply_surgical_diff(element, entry.change_type):
        diffs = compute_surgical_diffs(element_text, replacement_text)
        if diffs is not None:
            # Validation gate: verify accepted-view matches replacement
            accepted_view = "".join(text for op, text in diffs if op >= 0)
            if accepted_view != replacement_text:
                logger.warning(
                    "Validation gate failed for %s: accepted-view "
                    "'%s' != replacement '%s'. Falling back to wholesale.",
                    entry.change_id, accepted_view, replacement_text,
                )
            else:
                next_id = _apply_surgical(
                    element, entry.change_type, diffs,
                    client_author, timestamp, next_id,
                )
                return ActionOutcome(
                    action_type="counter_propose",
                    target_id=entry.change_id,
                    status="success",
                    original_text=entry.changed_text,
                    new_text=replacement_text,
                    method="surgical",
                ), next_id

    # Wholesale fallback
    next_id = _apply_wholesale(
        element, entry.change_type, replacement_text,
        client_author, timestamp, next_id,
    )
    return ActionOutcome(
        action_type="counter_propose",
        target_id=entry.change_id,
        status="success",
        original_text=entry.changed_text,
        new_text=replacement_text,
        method="wholesale",
    ), next_id


def _apply_surgical(
    element, change_type: str, diffs: list[tuple[int, str]],
    client_author: str, timestamp: str, next_id: int,
) -> int:
    """Route to the appropriate surgical counter-propose function."""
    if change_type == "insertion":
        return apply_surgical_insertion_counter_propose(
            element, diffs, client_author, timestamp, next_id,
        )
    return apply_surgical_deletion_counter_propose(
        element, diffs, client_author, timestamp, next_id,
    )


def _apply_wholesale(
    element, change_type: str, replacement_text: str,
    client_author: str, timestamp: str, next_id: int,
) -> int:
    """Route to the existing wholesale counter-propose functions."""
    if change_type == "insertion":
        return counter_propose_insertion(
            element, client_author, timestamp, replacement_text, next_id,
        )
    return counter_propose_deletion(
        element, client_author, timestamp, replacement_text, next_id,
    )
