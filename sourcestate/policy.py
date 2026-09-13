from __future__ import annotations

from typing import Iterable, List

from .domain import AccessState, Claim, SourceRecord
from .util import normalize_text


INSPECTABLE_STATES = {AccessState.FULL_TEXT, AccessState.PARTIAL_TEXT}


def can_use_content(source: SourceRecord) -> bool:
    return source.access_state in INSPECTABLE_STATES and source.pages_with_text > 0


def metadata_sources_named_in_claim(claim: Claim, sources: Iterable[SourceRecord]) -> List[SourceRecord]:
    low_claim = normalize_text(claim.text).lower()
    hits: List[SourceRecord] = []
    for source in sources:
        if source.access_state != AccessState.METADATA_ONLY:
            continue
        tokens = [t.lower() for t in source.title.replace("/", " ").split() if len(t) >= 3 and not t.isdigit()]
        if len(tokens) >= 2 and sum(t in low_claim for t in tokens) >= min(2, len(tokens)):
            hits.append(source)
        elif source.source_id in claim.cited_source_ids:
            hits.append(source)
    return hits


def source_policy_summary() -> dict:
    return {
        "metadata_is_not_full_text": True,
        "unseen_source_cannot_be_content_verified": True,
        "partial_text_is_never_represented_as_complete_full_text": True,
        "ocr_and_translation_are_transformations_not_originals": True,
        "claim_confirmation_required_before_research_mode_audit": True,
        "support_and_limitation_passes_are_independent": True,
        "human_review_required_for_all_claim_assessments": True,
        "candidate_labels_are_not_final_scholarly_judgments": True,
    }
