"""In-memory accept operation for the atomic pipeline.

Accepts tracked changes on a pre-loaded Document object without any file I/O.
The caller provides a Document and pre-resolved TrackedChangeEntry list.
This module does NOT call build_state_of_play(), Document(path), or .save().

Reuses find_tracked_change_element and accept_element from accept_helpers.
Returns ActionOutcome records compatible with the pipeline result model.
"""

from docx.document import Document

from src.models.change import TrackedChangeEntry
from src.negotiation.accept_helpers import accept_element, find_tracked_change_element
from src.pipeline.results import ActionOutcome


def accept_changes_on_document(
    document: Document,
    resolutions: list[TrackedChangeEntry],
) -> list[ActionOutcome]:
    """Accept tracked changes on an in-memory Document.

    For each resolution, finds the tracked change element by ooxml_id
    and accepts it (unwrap w:ins or remove w:del). Returns an
    ActionOutcome for each resolution indicating success or failure.

    Args:
        document: A pre-loaded python-docx Document object.
        resolutions: List of TrackedChangeEntry objects to accept.

    Returns:
        List of ActionOutcome records with status for each acceptance.
    """
    outcomes: list[ActionOutcome] = []
    body = document.element.body

    for entry in resolutions:
        element = find_tracked_change_element(body, entry.ooxml_id)
        if element is None:
            outcomes.append(ActionOutcome(
                action_type="accept",
                target_id=entry.change_id,
                status="failed",
                reason=f"XML element not found for ooxml_id={entry.ooxml_id}",
                original_text=entry.changed_text,
            ))
            continue

        accept_element(element)
        outcomes.append(ActionOutcome(
            action_type="accept",
            target_id=entry.change_id,
            status="success",
            original_text=entry.changed_text,
        ))

    return outcomes
