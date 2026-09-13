from __future__ import annotations

import re
from typing import Iterable, List

from .domain import Claim
from .util import normalize_text

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])")


def extract_claim_candidates(draft: str) -> List[str]:
    draft = normalize_text(draft)
    if not draft:
        return []
    out: List[str] = []
    for part in SENTENCE_SPLIT.split(draft):
        part = part.strip(" \n\t•-")
        if not part or part.endswith("?"):
            continue
        if len(part.split()) >= 5:
            out.append(part)
    return out


def confirmed_claims(lines: Iterable[str]) -> List[Claim]:
    claims: List[Claim] = []
    for idx, line in enumerate(lines, start=1):
        text = normalize_text(line)
        if not text:
            continue
        claims.append(Claim(claim_id=f"C{idx:03d}", text=text, user_confirmed=True))
    return claims


def parse_confirmed_claim_text(text: str) -> List[Claim]:
    lines = []
    for raw in (text or "").splitlines():
        raw = re.sub(r"^\s*(?:C\d+[\).:-]?|\d+[\).:-]|[-*•])\s*", "", raw, flags=re.IGNORECASE).strip()
        if raw:
            lines.append(raw)
    return confirmed_claims(lines)
