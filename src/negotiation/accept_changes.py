"""Selective accept-changes function for tracked change negotiation.

Provides accept_changes() which takes an input .docx path, an output
.docx path, and a list of Chg:N IDs. It validates all inputs upfront
(fail-fast), performs the OOXML mutations, saves to the output path,
and returns a structured AcceptResult.

This is the first negotiation mutation operation. It uses the state-of-play
from Phase 4 for change_id to ooxml_id resolution, then directly
manipulates XML elements to accept tracked changes.
"""

from docx import Document

from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.accept import AcceptedChange, AcceptError, AcceptResult
from src.models.change import StateOfPlay, TrackedChangeEntry
from src.negotiation.accept_helpers import (
    accept_element,
    find_tracked_change_element,
    validate_output_path,
)
from src.validation.output_validator import validate_docx_output


def accept_changes(
    input_path: str, output_path: str, change_ids: list[str]
) -> AcceptResult:
    """Accept tracked changes by Chg:N ID, writing the result to output_path.

    Validates all inputs and change IDs upfront before any mutation. If any
    ID is invalid (wrong format, nonexistent, or a comment), raises
    AcceptError with no changes applied and no output file created.

    Args:
        input_path: Path to the input .docx document.
        output_path: Path for the output .docx document (must not exist).
        change_ids: List of Chg:N IDs to accept.

    Returns:
        AcceptResult listing all accepted changes with their metadata.

    Raises:
        AcceptError: If any ID is invalid, not found, or is a comment.
        IngestionError: If the input path is invalid.
    """
    validate_docx_path(input_path)
    validated_output = validate_output_path(output_path)

    state = build_state_of_play(input_path)
    resolutions = _resolve_all_change_ids(state, change_ids)

    document = Document(input_path)
    accepted = _accept_resolved_changes(document, resolutions)

    output_str = str(validated_output)
    document.save(output_str)
    warnings = validate_docx_output(output_str)
    return AcceptResult(accepted_changes=accepted, validation_warnings=warnings)


def _resolve_all_change_ids(
    state: StateOfPlay, change_ids: list[str]
) -> list[TrackedChangeEntry]:
    """Resolve all change IDs to TrackedChangeEntry objects.

    Validates that each ID has the Chg: prefix (not Com:), and that
    it exists in the state-of-play. This is the fail-fast validation
    step -- if any ID is invalid, the entire batch is rejected.

    Args:
        state: The state-of-play for the document.
        change_ids: List of Chg:N IDs to resolve.

    Returns:
        List of TrackedChangeEntry objects matching the requested IDs.

    Raises:
        AcceptError: If any ID is a comment or does not exist.
    """
    resolutions: list[TrackedChangeEntry] = []
    for change_id in change_ids:
        if change_id.startswith("Com:"):
            raise AcceptError(
                f"Cannot accept comment {change_id} -- "
                "use comment operations instead"
            )
        entry = _find_entry_by_change_id(state, change_id)
        if entry is None:
            raise AcceptError(f"Change not found: {change_id}")
        resolutions.append(entry)
    return resolutions


def _find_entry_by_change_id(
    state: StateOfPlay, change_id: str
) -> TrackedChangeEntry | None:
    """Find a TrackedChangeEntry by its change_id in the state-of-play.

    Args:
        state: The state-of-play containing all tracked changes.
        change_id: The Chg:N identifier to look up.

    Returns:
        The matching TrackedChangeEntry, or None if not found.
    """
    for entry in state.changes:
        if entry.change_id == change_id:
            return entry
    return None


def _accept_resolved_changes(
    document: Document, resolutions: list[TrackedChangeEntry]
) -> list[AcceptedChange]:
    """Accept each resolved change by finding and manipulating its XML element.

    Looks up each tracked change element by ooxml_id in the document body,
    then applies the accept operation. Returns a list of AcceptedChange
    records for the result.

    Args:
        document: The python-docx Document loaded for mutation.
        resolutions: List of resolved TrackedChangeEntry objects.

    Returns:
        List of AcceptedChange records for each accepted change.

    Raises:
        AcceptError: If an XML element cannot be found for a resolved change.
    """
    accepted: list[AcceptedChange] = []
    for entry in resolutions:
        element = find_tracked_change_element(
            document.element.body, entry.ooxml_id
        )
        if element is None:
            raise AcceptError(
                f"XML element not found for {entry.change_id} "
                f"(ooxml_id={entry.ooxml_id})"
            )
        accept_element(element)
        accepted.append(
            AcceptedChange(
                change_id=entry.change_id,
                change_type=entry.change_type,
                text=entry.changed_text,
            )
        )
    return accepted
