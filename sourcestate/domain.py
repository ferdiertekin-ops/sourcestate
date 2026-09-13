from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AccessState(str, Enum):
    METADATA_ONLY = "metadata_only"
    FULL_TEXT = "full_text"
    PARTIAL_TEXT = "partial_text"
    FILE_PRESENT_UNREADABLE = "file_present_unreadable"


class AuditMode(str, Enum):
    DEMO = "demo"
    RESEARCH = "research"


class AssessmentStatus(str, Enum):
    SUPPORT_CANDIDATE = "SUPPORT CANDIDATE"
    CONFLICT_CANDIDATE = "CONFLICT CANDIDATE"
    WEAK_MATCH = "WEAK MATCH"
    UNVERIFIED = "UNVERIFIED"
    VERIFICATION_BLOCKED = "VERIFICATION BLOCKED"


class FitLabel(str, Enum):
    MATCH = "match"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class EvidenceDirection(str, Enum):
    SUPPORT = "support"
    LIMITATION = "limitation"


class HumanDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass(frozen=True)
class TransformationStep:
    step_id: str
    kind: str
    tool: str
    tool_version: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None


@dataclass
class SourceRecord:
    source_id: str
    title: str
    access_state: AccessState
    filename: Optional[str] = None
    file_sha256: Optional[str] = None
    pages_total: int = 0
    pages_with_text: int = 0
    pages_ocr: int = 0
    locator: Optional[str] = None
    note: str = ""


@dataclass
class SourcePage:
    source_id: str
    source_title: str
    page_number: int
    text: str
    text_sha256: str
    transformations: List[TransformationStep] = field(default_factory=list)


@dataclass
class Claim:
    claim_id: str
    text: str
    user_confirmed: bool
    cited_source_ids: List[str] = field(default_factory=list)


@dataclass
class EvidenceSnippet:
    source_id: str
    source_title: str
    page_number: int
    score: float
    excerpt: str
    text_sha256: str
    transformations: List[TransformationStep]


@dataclass
class DimensionAssessment:
    dimension: str
    label: FitLabel
    rationale: str


@dataclass
class HistoricalClaimFit:
    dimensions: List[DimensionAssessment]

    @property
    def conflicts(self) -> int:
        return sum(1 for d in self.dimensions if d.label == FitLabel.CONFLICT)

    @property
    def partials(self) -> int:
        return sum(1 for d in self.dimensions if d.label == FitLabel.PARTIAL)


@dataclass
class PassResult:
    direction: EvidenceDirection
    evidence: List[EvidenceSnippet]
    fit: Optional[HistoricalClaimFit]
    rationale: str


@dataclass
class ClaimAssessment:
    claim: Claim
    status: AssessmentStatus
    rationale: str
    support_pass: PassResult
    limitation_pass: PassResult
    human_review_required: bool = True
    human_decision: HumanDecision = HumanDecision.PENDING


@dataclass
class AuditEvent:
    event_id: str
    time_utc: str
    action: str
    detail: Dict[str, Any]


@dataclass
class AuditConfig:
    top_k: int = 5
    support_threshold: float = 0.27
    weak_threshold: float = 0.12
    conflict_min_similarity: float = 0.20


@dataclass
class AuditSession:
    session_id: str
    mode: AuditMode
    draft_sha256: str
    created_at_utc: str
    config: AuditConfig
    claims: List[Claim]
    sources: List[SourceRecord]
    assessments: List[ClaimAssessment]
    events: List[AuditEvent]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
