from __future__ import annotations

from typing import Protocol

from .domain import HistoricalClaimFit


class SemanticJudge(Protocol):
    """Future plug-in boundary for an LLM or local NLI model.

    v0.3 does not ship a network implementation. Any future adapter must receive
    only policy-cleared evidence and must return structured analysis that remains
    subordinate to the provenance record and human review.
    """
    def compare(self, claim: str, evidence: str) -> HistoricalClaimFit:
        ...
