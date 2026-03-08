"""Anchor module -- clean-text position mapping and anchored edit application.

Extracted from local adeu fork (not in upstream adeu v0.7.0).
Provides apply_anchored_edit for auto-layering counter-proposals.
"""

from src.anchor.anchor import AnchorMap, AnchorSpan, apply_anchored_edit, classify_edit_context

__all__ = ["AnchorMap", "AnchorSpan", "apply_anchored_edit", "classify_edit_context"]
