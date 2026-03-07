"""Group executor for the negotiation pipeline.

Executes sorted action groups on a pre-loaded Document object with
skip-and-continue error handling. Each group dispatches to the
corresponding in-memory operation and produces ActionOutcome records.
Failed groups are skipped but do not abort subsequent groups.

ID resolution uses stable OOXML w:id values from a pre-built map,
eliminating the need for re-ingestion between operation groups.

Usage:
    from src.pipeline.executor import execute_action_groups

    outcomes = execute_action_groups(document, state, sorted_actions, author_config)
"""

from itertools import groupby

from docx.document import Document

from src.models.author_config import AuthorConfig
from src.models.change import StateOfPlay
from src.negotiation.accept_changes_inplace import accept_changes_on_document
from src.negotiation.add_comments_inplace import add_comments_on_document
from src.negotiation.counter_propose_inplace import counter_propose_on_document
from src.negotiation.reply_inplace import reply_on_document
from src.negotiation.resolve_inplace import resolve_on_document
from src.pipeline.actions import NegotiationAction
from src.pipeline.executor_helpers import (
    build_failed_outcomes,
    resolve_accept_group,
    resolve_add_comment_group,
    resolve_counter_propose_group,
    resolve_reply_group,
    resolve_resolve_group,
)
from src.pipeline.id_remapper import build_id_to_ooxml_map
from src.pipeline.results import ActionOutcome


def execute_action_groups(
    document: Document,
    state: StateOfPlay,
    sorted_actions: list[NegotiationAction],
    author_config: AuthorConfig,
) -> list[ActionOutcome]:
    """Execute sorted action groups on an in-memory Document.

    Groups actions by action_type (already sorted), resolves each
    action's target through the stable ooxml_id bridge, and dispatches
    to in-memory operations. No file I/O occurs -- all mutations
    happen on the provided Document object.

    After accept groups, the accepted ooxml_ids are known (they were
    in the action list) so no re-ingestion is needed. The id_to_ooxml
    map remains valid because ooxml w:id attributes are stable.

    Args:
        document: A pre-loaded python-docx Document object.
        state: Pre-built state of play from the original document.
        sorted_actions: Actions pre-sorted by execution order.
        author_config: Client author config for attribution.

    Returns:
        List of ActionOutcome for every action (success or failed).
    """
    all_outcomes: list[ActionOutcome] = []
    id_to_ooxml = build_id_to_ooxml_map(state)
    groups = _materialize_groups(sorted_actions)

    for action_type, group_actions in groups:
        outcomes = _execute_single_group(
            action_type, group_actions, document,
            state, id_to_ooxml, author_config,
        )
        all_outcomes.extend(outcomes)

    return all_outcomes


def _materialize_groups(
    sorted_actions: list[NegotiationAction],
) -> list[tuple[str, list[NegotiationAction]]]:
    """Materialize groupby into a list so we can iterate reliably."""
    return [
        (action_type, list(group_iter))
        for action_type, group_iter in groupby(
            sorted_actions, key=lambda a: a.action_type
        )
    ]


def _execute_single_group(
    action_type: str,
    actions: list[NegotiationAction],
    document: Document,
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
    author_config: AuthorConfig,
) -> list[ActionOutcome]:
    """Execute a single action group with skip-and-continue error handling.

    On success, returns per-action outcomes. On failure, returns failed
    outcomes for every action in the group.
    """
    try:
        return _dispatch_group(
            action_type, actions, document,
            state, id_to_ooxml, author_config,
        )
    except Exception as exc:
        return build_failed_outcomes(actions, exc)


def _dispatch_group(
    action_type: str,
    actions: list[NegotiationAction],
    document: Document,
    state: StateOfPlay,
    id_to_ooxml: dict[str, str],
    author_config: AuthorConfig,
) -> list[ActionOutcome]:
    """Dispatch to the appropriate in-memory operation."""
    if action_type == "accept":
        entries = resolve_accept_group(actions, state, id_to_ooxml)
        return accept_changes_on_document(document, entries)

    if action_type == "counter_propose":
        resolutions = resolve_counter_propose_group(
            actions, state, id_to_ooxml,
        )
        return counter_propose_on_document(
            document, resolutions, author_config,
        )

    if action_type == "add_comment":
        resolutions = resolve_add_comment_group(
            actions, state, id_to_ooxml,
        )
        return add_comments_on_document(
            document, resolutions, author_config,
        )

    if action_type == "reply":
        resolutions = resolve_reply_group(actions, state, id_to_ooxml)
        return reply_on_document(document, resolutions, author_config)

    if action_type == "resolve":
        entries, original_ids = resolve_resolve_group(
            actions, state, id_to_ooxml,
        )
        return resolve_on_document(
            document, entries, original_ids, state,
        )

    raise ValueError(f"Unknown action type: {action_type}")
