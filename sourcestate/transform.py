from __future__ import annotations

from dataclasses import replace

from .domain import SourcePage, TransformationStep
from .util import new_id, sha256_text

ALLOWED_DERIVATIONS = {"transcription", "translation", "normalization", "manual_correction"}


def derive_page_text(
    parent: SourcePage,
    new_text: str,
    kind: str,
    tool: str,
    tool_version: str | None = None,
    parameters: dict | None = None,
) -> SourcePage:
    """Create a derived text artifact while preserving append-only lineage.

    This function never mutates the parent page. The parent text hash becomes the
    new transformation's input hash; the derived text receives a new output hash.
    """
    if kind not in ALLOWED_DERIVATIONS:
        raise ValueError(f"Unsupported derivation kind: {kind}")
    output_hash = sha256_text(new_text)
    step = TransformationStep(
        step_id=new_id("xfm"), kind=kind, tool=tool, tool_version=tool_version,
        parameters=parameters or {}, input_hash=parent.text_sha256,
        output_hash=output_hash,
    )
    return replace(
        parent,
        text=new_text,
        text_sha256=output_hash,
        transformations=[*parent.transformations, step],
    )
