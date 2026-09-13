from __future__ import annotations

from typing import List, Optional, Tuple

from .domain import EvidenceDirection, EvidenceSnippet, PassResult
from .fit import hard_conflict_reason, historical_claim_fit


class SupportReviewPass:
    """Looks only for the strongest support candidate. It never sees limitation-pass output."""

    def run(self, claim: str, candidates: List[EvidenceSnippet], support_threshold: float, weak_threshold: float) -> PassResult:
        if not candidates:
            return PassResult(EvidenceDirection.SUPPORT, [], None, "No inspectable evidence candidates were retrieved.")
        best = candidates[0]
        fit = historical_claim_fit(claim, best)
        if best.score >= support_threshold and fit.conflicts == 0:
            rationale = "A closely matching inspected passage was found without a deterministic hard-conflict signal."
        elif best.score >= weak_threshold:
            rationale = "A potentially relevant inspected passage was found, but support is weak or dimension checks require caution."
        else:
            rationale = "No sufficiently close inspected passage was found."
        return PassResult(EvidenceDirection.SUPPORT, [best], fit, rationale)


class LimitationReviewPass:
    """Independently scans all retrieved candidates for contrary/limiting signals."""

    def run(self, claim: str, candidates: List[EvidenceSnippet], min_similarity: float) -> PassResult:
        hits: List[EvidenceSnippet] = []
        reasons: List[str] = []
        for candidate in candidates:
            reason = hard_conflict_reason(claim, candidate.excerpt, candidate.score, min_similarity)
            if reason:
                hits.append(candidate)
                reasons.append(reason)
        fit = historical_claim_fit(claim, hits[0]) if hits else None
        rationale = " | ".join(dict.fromkeys(reasons)) if reasons else "No deterministic contrary/limiting signal was found in the retrieved candidate set."
        return PassResult(EvidenceDirection.LIMITATION, hits, fit, rationale)
