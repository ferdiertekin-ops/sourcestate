from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .domain import AccessState, AssessmentStatus, AuditMode, Claim, SourcePage, SourceRecord, TransformationStep
from .util import new_id, sha256_text
from .workflow import AuditEngine


@dataclass
class BenchmarkCase:
    name: str
    claim: str
    expected: AssessmentStatus
    pages: List[SourcePage]
    sources: List[SourceRecord]


def _page(source_id: str, title: str, text: str, kind: str = "pdf_text_extraction") -> SourcePage:
    step = TransformationStep(new_id("xfm"), kind, "fixture", output_hash=sha256_text(text))
    return SourcePage(source_id, title, 1, text, sha256_text(text), [step])


def built_in_cases() -> List[BenchmarkCase]:
    return [
        BenchmarkCase(
            "exact-support",
            "The event occurred on 29 February 1880 in the capital.",
            AssessmentStatus.SUPPORT_CANDIDATE,
            [_page("a", "Alpha", "The event occurred on 29 February 1880 in the capital.")],
            [SourceRecord("a", "Alpha", AccessState.FULL_TEXT, pages_total=1, pages_with_text=1)],
        ),
        BenchmarkCase(
            "secondary-date-conflict",
            "The event occurred on 29 February 1880 in the capital.",
            AssessmentStatus.CONFLICT_CANDIDATE,
            [
                _page("a", "Alpha", "The event occurred on 29 February 1880 in the capital."),
                _page("b", "Beta", "A later memorandum dates the event to 1 March 1880 in the capital."),
            ],
            [
                SourceRecord("a", "Alpha", AccessState.FULL_TEXT, pages_total=1, pages_with_text=1),
                SourceRecord("b", "Beta", AccessState.FULL_TEXT, pages_total=1, pages_with_text=1),
            ],
        ),
        BenchmarkCase(
            "metadata-block",
            "Archive Bulletin Gamma 1912 proves that the committee met in April.",
            AssessmentStatus.VERIFICATION_BLOCKED,
            [],
            [SourceRecord("m", "Archive Bulletin Gamma 1912", AccessState.METADATA_ONLY)],
        ),
        BenchmarkCase(
            "negation-conflict",
            "The committee approved the proposal on 4 April 1909.",
            AssessmentStatus.CONFLICT_CANDIDATE,
            [_page("n", "Negative", "The committee did not approve the proposal on 4 April 1909.")],
            [SourceRecord("n", "Negative", AccessState.FULL_TEXT, pages_total=1, pages_with_text=1)],
        ),
    ]


def run_benchmark() -> dict:
    engine = AuditEngine()
    details = []
    correct = 0
    for case in built_in_cases():
        claim = Claim("C001", case.claim, True)
        session = engine.run(case.claim, [claim], case.sources, case.pages, mode=AuditMode.DEMO)
        actual = session.assessments[0].status
        ok = actual == case.expected
        correct += int(ok)
        details.append({"case": case.name, "expected": case.expected.value, "actual": actual.value, "pass": ok})
    return {"cases": len(details), "correct": correct, "accuracy": correct / len(details) if details else 0.0, "details": details}
