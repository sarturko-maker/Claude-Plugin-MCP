"""Styler callback interface and data models for formatting correction.

The Styler is the final pipeline step -- a deterministic extraction of
client-authored OOXML paragraphs with surrounding context, presented to
an external LLM callback for formatting correction. The pipeline engine
remains LLM-free: extraction and splicing are pure Python, only the
callback itself invokes the LLM.

OoxmlTriplet captures a target paragraph plus its neighbors as raw OOXML.
OoxmlFragment carries the corrected XML back for splicing.
StylerCallback is the Protocol that external callers implement.

Usage:
    from src.pipeline.styler import StylerCallback, OoxmlTriplet, OoxmlFragment

    class MyStyler:
        def fix_formatting(self, triplets: list[OoxmlTriplet]) -> list[OoxmlFragment]:
            # Send to LLM, get corrections back
            ...
"""

from typing import Protocol

from pydantic import BaseModel


class OoxmlTriplet(BaseModel):
    """A client-authored paragraph with surrounding context as raw OOXML.

    Attributes:
        paragraph_above: Raw OOXML of the paragraph above (empty if first).
        target_paragraph: Raw OOXML of the client-authored paragraph.
        paragraph_below: Raw OOXML of the paragraph below (empty if last).
        paragraph_index: Position in the document body paragraph list.
    """

    paragraph_above: str
    target_paragraph: str
    paragraph_below: str
    paragraph_index: int


class OoxmlFragment(BaseModel):
    """A corrected OOXML fragment to splice back into the document.

    Attributes:
        paragraph_index: Position in the document body paragraph list.
        corrected_xml: The corrected raw OOXML string for this paragraph.
    """

    paragraph_index: int
    corrected_xml: str


class StylerCallback(Protocol):
    """Protocol for external LLM formatting correction.

    Implementors receive a list of OoxmlTriplet (client-authored paragraphs
    with context) and return a list of OoxmlFragment with corrected XML.
    The callback is sync per project conventions (local CLI tool, single
    batched LLM call).
    """

    def fix_formatting(
        self, triplets: list[OoxmlTriplet],
    ) -> list[OoxmlFragment]:
        """Receive OOXML triplets and return corrected fragments.

        Args:
            triplets: Client-authored paragraphs with surrounding context.

        Returns:
            List of corrected fragments to splice back into the document.
        """
        ...
