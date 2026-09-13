from __future__ import annotations

import uuid
from typing import List, Sequence, Tuple

from .domain import (
    AssessmentStatus, AuditConfig, AuditEvent, AuditMode, AuditSession, Claim,
    ClaimAssessment, EvidenceDirection, PassResult, SourcePage, SourceRecord,
)
from .ingest import event
from .passes import LimitationReviewPass, SupportReviewPass
from .policy import metadata_sources_named_in_claim, source_policy_summary
from .retrieval import TfidfEvidenceRetriever
from .util import now_iso, sha256_text

VERSION = "0.3.0"


class AuditEngine:
    def __init__(self, config: AuditConfig | None = None):
        self.config = config or AuditConfig()
        self.support_pass = SupportReviewPass()
        self.limitation_pass = LimitationReviewPass()

    def _blocked_assessment(self, claim: Claim, named: Sequence[SourceRecord]) -> ClaimAssessment:
        empty_support = PassResult(EvidenceDirection.SUPPORT, [], None, "Content verification blocked by source-state policy.")
        empty_limit = PassResult(EvidenceDirection.LIMITATION, [], None, "Content verification blocked by source-state policy.")
        rationale = "The claim invokes a metadata-only source. Source content has not been inspected; content verification is not permitted."
        return ClaimAssessment(claim, AssessmentStatus.VERIFICATION_BLOCKED, rationale, empty_support, empty_limit)

    def run(
        self, draft: str, claims: Sequence[Claim], sources: Sequence[SourceRecord], pages: Sequence[SourcePage],
        mode: AuditMode = AuditMode.RESEARCH, pre_events: Sequence[AuditEvent] | None = None,
        warnings: Sequence[str] | None = None,
    ) -> AuditSession:
        if mode == AuditMode.RESEARCH and any(not c.user_confirmed for c in claims):
            raise ValueError("Research-mode audit requires user-confirmed claims.")

        events: List[AuditEvent] = list(pre_events or [])
        events.append(event("policy_loaded", source_policy_summary()))
        retriever = TfidfEvidenceRetriever(pages)
        assessments: List[ClaimAssessment] = []

        for claim in claims:
            named_metadata = metadata_sources_named_in_claim(claim, sources)
            if named_metadata:
                assessment = self._blocked_assessment(claim, named_metadata)
                assessments.append(assessment)
                events.append(event("metadata_guard_enforced", {
                    "claim_id": claim.claim_id,
                    "metadata_source_ids": [s.source_id for s in named_metadata],
                }))
                continue

            candidates = retriever.retrieve(claim.text, self.config.top_k)
            # These passes are intentionally independent: neither receives the other's output.
            support = self.support_pass.run(claim.text, list(candidates), self.config.support_threshold, self.config.weak_threshold)
            limitation = self.limitation_pass.run(claim.text, list(candidates), self.config.conflict_min_similarity)

            if limitation.evidence:
                status = AssessmentStatus.CONFLICT_CANDIDATE
                rationale = limitation.rationale + " Human review is required; this is not a final contradiction judgment."
            elif support.evidence and support.evidence[0].score >= self.config.support_threshold and support.fit and support.fit.conflicts == 0:
                status = AssessmentStatus.SUPPORT_CANDIDATE
                rationale = support.rationale + " Human review must confirm historical support."
            elif support.evidence and support.evidence[0].score >= self.config.weak_threshold:
                status = AssessmentStatus.WEAK_MATCH
                rationale = support.rationale
            else:
                status = AssessmentStatus.UNVERIFIED
                rationale = "Inspectable supplied sources were searched, but no sufficiently related passage was found."

            assessment = ClaimAssessment(claim, status, rationale, support, limitation)
            assessments.append(assessment)
            events.append(event("claim_assessed", {
                "claim_id": claim.claim_id, "status": status.value,
                "support_source": support.evidence[0].source_id if support.evidence else None,
                "support_page": support.evidence[0].page_number if support.evidence else None,
                "support_score": support.evidence[0].score if support.evidence else None,
                "limitation_hits": len(limitation.evidence),
            }))

        return AuditSession(
            session_id=f"audit:{uuid.uuid4().hex}", mode=mode,
            draft_sha256=sha256_text(draft), created_at_utc=now_iso(), config=self.config,
            claims=list(claims), sources=list(sources), assessments=assessments,
            events=events, warnings=list(warnings or []),
        )
