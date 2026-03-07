"""First-pass redlining pipeline for clean documents.

Provides run_first_pass_pipeline() which reads a clean .docx, applies
tracked changes via word-level surgical diff routing (falling back to
Adeu's wholesale engine.apply_edits() for edge cases), optionally runs
the Styler formatting pass, validates the output, and returns a
structured RedlineResult with per-edit outcome tracking.

Intentionally separate from orchestrator.py -- clean documents do not
need state-of-play, action groups, or ID remapping.

Usage:
    from src.pipeline.first_pass import run_first_pass_pipeline

    result = run_first_pass_pipeline(
        input_path="clean.docx",
        output_path="redlined.docx",
        edits=[DocumentEdit(target_text="old", new_text="new")],
        author_config=AuthorConfig(name="Client Firm"),
    )
"""

import shutil
from io import BytesIO
from pathlib import Path

from adeu import DocumentEdit, RedlineEngine

from src.ingestion.validation import validate_docx_path
from src.models.author_config import AuthorConfig
from src.pipeline.first_pass_result import RedlineResult
from src.pipeline.results import StylerReport
from src.pipeline.styler import StylerCallback
from src.pipeline.styler_extraction import (
    extract_client_triplets,
    splice_corrected_fragments,
)
from src.pipeline.surgical_edit import apply_edits_surgically
from src.validation.output_validator import validate_docx_output


def run_first_pass_pipeline(
    input_path: str,
    output_path: str,
    edits: list[DocumentEdit],
    author_config: AuthorConfig,
    styler: StylerCallback | None = None,
) -> RedlineResult:
    """Apply tracked changes to a clean document and return structured results.

    Validates paths, applies edits via RedlineEngine, identifies skipped
    edits, runs optional Styler pass, validates output, and returns a
    RedlineResult with per-edit outcomes.

    Raises IngestionError if input_path is invalid, ValueError if
    output_path is invalid.
    """
    validate_docx_path(input_path)
    _validate_output_path(output_path)

    if not edits:
        shutil.copy2(input_path, output_path)
        return RedlineResult(
            output_path=output_path, applied=[], skipped=[],
        )

    with open(input_path, "rb") as f:
        doc_stream = BytesIO(f.read())

    engine = RedlineEngine(doc_stream, author=author_config.name)
    applied, skipped = apply_edits_surgically(engine, edits)

    output_stream = engine.save_to_stream()
    with open(output_path, "wb") as f:
        f.write(output_stream.read())

    styler_report = None
    if styler is not None:
        styler_report = _run_styler_step(
            output_path, author_config.name, styler,
        )

    warnings = validate_docx_output(output_path)

    return RedlineResult(
        output_path=output_path,
        applied=applied,
        skipped=skipped,
        styler_report=styler_report,
        validation_warnings=warnings,
    )


def _run_styler_step(
    output_path: str,
    client_author: str,
    styler: StylerCallback,
) -> StylerReport:
    """Run the Styler extraction/correction/splicing step.

    Extracts client-authored OOXML triplets, passes them to the
    StylerCallback, and splices corrected fragments back in-place.
    """
    triplets = extract_client_triplets(output_path, client_author)
    fragments = []

    if triplets:
        fragments = styler.fix_formatting(triplets)
        if fragments:
            splice_corrected_fragments(output_path, output_path, fragments)

    return StylerReport(
        triplets_extracted=len(triplets),
        triplets_corrected=len(fragments),
        details=[
            f"Corrected paragraph at index {f.paragraph_index}"
            for f in fragments
        ],
    )


def _validate_output_path(output_path: str) -> None:
    """Validate the output path: .docx extension, parent exists, no traversal."""
    path = Path(output_path)

    if ".." in path.parts:
        raise ValueError("Invalid output path: path traversal detected")

    if path.suffix.lower() != ".docx":
        raise ValueError("Output path must end with .docx")

    if not path.parent.exists():
        raise ValueError(
            f"Output directory does not exist: {path.parent.name}"
        )
