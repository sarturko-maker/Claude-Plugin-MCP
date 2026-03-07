"""Counter-proposal function for tracked change negotiation.

Provides counter_propose_changes() which takes an input .docx path, an output
.docx path, a list of (change_id, replacement_text) proposals, and an
AuthorConfig. It validates all inputs upfront (fail-fast), layers client-attributed
redlines on top of counterparty markup, saves to the output path, validates
the output, and returns a structured CounterProposalResult.

This is the core negotiation operation -- it enables the client to respond to
each counterparty change with their own tracked changes, preserving the full
audit trail required for legal contract negotiations.
"""

from docx import Document

from src.ingestion.state_of_play import build_state_of_play
from src.ingestion.validation import validate_docx_path
from src.models.author_config import AuthorConfig
from src.models.change import TrackedChangeEntry
from src.models.counter_proposal import (
    CounterProposalError,
    CounterProposedChange,
    CounterProposalResult,
)
from src.negotiation.accept_helpers import (
    find_tracked_change_element,
    validate_output_path,
)
from src.negotiation.counter_propose_helpers import (
    counter_propose_deletion,
    counter_propose_insertion,
    get_max_revision_id,
)
from src.negotiation.timestamp import generate_timestamp
from src.validation.output_validator import validate_docx_output


def counter_propose_changes(
    input_path: str,
    output_path: str,
    proposals: list[tuple[str, str]],
    author_config: AuthorConfig,
) -> CounterProposalResult:
    """Counter-propose tracked changes by layering client redlines on counterparty markup.

    Validates all inputs and proposals upfront before any mutation. If any
    change_id is invalid, a comment, nonexistent, or violates replacement
    rules, raises CounterProposalError with no changes applied.

    Args:
        input_path: Path to the input .docx document.
        output_path: Path for the output .docx document.
        proposals: List of (change_id, replacement_text) tuples.
        author_config: Client author configuration for attribution.

    Returns:
        CounterProposalResult listing all applied counter-proposals.

    Raises:
        CounterProposalError: If any proposal is invalid.
        IngestionError: If the input path is invalid.
    """
    validate_docx_path(input_path)
    _validate_output(output_path)

    state = build_state_of_play(input_path)
    resolutions = _resolve_all_proposals(state, proposals)

    document = Document(input_path)
    counter_proposals = _apply_counter_proposals(
        document, resolutions, author_config
    )

    validated_path = str(validate_output_path(output_path))
    document.save(validated_path)
    warnings = validate_docx_output(validated_path)
    return CounterProposalResult(
        counter_proposals=counter_proposals,
        validation_warnings=warnings,
    )


def _validate_output(output_path: str) -> None:
    """Validate the output path, re-raising AcceptError as CounterProposalError."""
    from src.models.accept import AcceptError

    try:
        validate_output_path(output_path)
    except AcceptError as exc:
        raise CounterProposalError(str(exc)) from exc


def _resolve_all_proposals(
    state: object,
    proposals: list[tuple[str, str]],
) -> list[tuple[TrackedChangeEntry, str]]:
    """Resolve all proposals to (TrackedChangeEntry, replacement_text) pairs.

    Fail-fast validation: rejects comment IDs, nonexistent IDs, and empty
    replacement text on deletion changes. If any proposal is invalid, the
    entire batch is rejected before any XML mutation occurs.
    """
    resolutions: list[tuple[TrackedChangeEntry, str]] = []

    for change_id, replacement_text in proposals:
        if change_id.startswith("Com:"):
            raise CounterProposalError(
                f"Cannot counter-propose comment {change_id} -- "
                "use comment operations instead"
            )

        entry = _find_entry_by_change_id(state, change_id)
        if entry is None:
            raise CounterProposalError(f"Change not found: {change_id}")

        if entry.change_type == "deletion" and not replacement_text:
            raise CounterProposalError(
                f"Cannot counter-propose deletion {change_id} with empty "
                "replacement text -- a deletion counter-proposal must "
                "provide alternative text"
            )

        resolutions.append((entry, replacement_text))

    return resolutions


def _find_entry_by_change_id(
    state: object, change_id: str
) -> TrackedChangeEntry | None:
    """Find a TrackedChangeEntry by its change_id in the state-of-play."""
    for entry in state.changes:
        if entry.change_id == change_id:
            return entry
    return None


def _apply_counter_proposals(
    document: Document,
    resolutions: list[tuple[TrackedChangeEntry, str]],
    author_config: AuthorConfig,
) -> list[CounterProposedChange]:
    """Apply each counter-proposal by finding and manipulating XML elements.

    Looks up each tracked change element by ooxml_id, dispatches to the
    appropriate OOXML helper, and builds a CounterProposedChange record.
    """
    body = document.element.body
    next_id = get_max_revision_id(body) + 1
    timestamp = generate_timestamp(author_config.date_override)
    client_author = author_config.name
    results: list[CounterProposedChange] = []

    for entry, replacement_text in resolutions:
        element = find_tracked_change_element(body, entry.ooxml_id)
        if element is None:
            raise CounterProposalError(
                f"XML element not found for {entry.change_id} "
                f"(ooxml_id={entry.ooxml_id})"
            )

        if entry.change_type == "insertion":
            next_id = counter_propose_insertion(
                element, client_author, timestamp, replacement_text, next_id
            )
        elif entry.change_type == "deletion":
            next_id = counter_propose_deletion(
                element, client_author, timestamp, replacement_text, next_id
            )

        results.append(
            CounterProposedChange(
                change_id=entry.change_id,
                original_text=entry.changed_text,
                replacement_text=replacement_text,
            )
        )

    return results
