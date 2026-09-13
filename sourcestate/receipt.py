from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from .domain import AuditSession
from .policy import source_policy_summary
from .workflow import VERSION


def session_payload(session: AuditSession) -> Dict[str, Any]:
    return {
        "tool": "SourceState",
        "version": VERSION,
        "session": asdict(session),
        "policy": source_policy_summary(),
    }


def write_audit_json(session: AuditSession, path: str | Path) -> str:
    path = str(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session_payload(session), f, ensure_ascii=False, indent=2, default=str)
    return path


def write_ledger_csv(session: AuditSession, path: str | Path) -> str:
    path = str(path)
    rows = []
    for a in session.assessments:
        support = a.support_pass.evidence[0] if a.support_pass.evidence else None
        limitation = a.limitation_pass.evidence[0] if a.limitation_pass.evidence else None
        rows.append({
            "claim_id": a.claim.claim_id,
            "claim": a.claim.text,
            "status": a.status.value,
            "support_source": support.source_title if support else "",
            "support_page": support.page_number if support else "",
            "support_score": round(support.score, 4) if support else "",
            "limitation_source": limitation.source_title if limitation else "",
            "limitation_page": limitation.page_number if limitation else "",
            "human_decision": a.human_decision.value,
            "rationale": a.rationale,
        })
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["claim_id"])
        writer.writeheader(); writer.writerows(rows)
    return path


def write_research_receipt(session: AuditSession, path: str | Path) -> str:
    path = Path(path)
    lines = [
        "# SourceState Research Receipt",
        "",
        f"- Version: {VERSION}",
        f"- Session: `{session.session_id}`",
        f"- Mode: `{session.mode.value}`",
        f"- Created (UTC): {session.created_at_utc}",
        f"- Draft SHA-256: `{session.draft_sha256}`",
        "- Scholarly status: machine-generated audit signals; human review remains required.",
        "",
        "## Source Registry",
    ]
    for s in session.sources:
        lines.extend([
            f"### {s.title}",
            f"- Source ID: `{s.source_id}`",
            f"- Access state: **{s.access_state.value}**",
            f"- File SHA-256: `{s.file_sha256 or 'not applicable'}`",
            f"- Inspectable pages: {s.pages_with_text}/{s.pages_total if s.pages_total else '—'}",
            f"- Policy note: {s.note}",
            "",
        ])
    lines.append("## Claim Audit")
    for a in session.assessments:
        lines.extend([
            f"### {a.claim.claim_id} — {a.status.value}",
            f"> {a.claim.text}",
            "",
            f"**Rationale:** {a.rationale}",
            f"**Human decision:** {a.human_decision.value}",
            "",
        ])
        if a.support_pass.evidence:
            e = a.support_pass.evidence[0]
            lines.extend([
                f"**Support candidate:** {e.source_title}, p. {e.page_number}, score {e.score:.3f}",
                f"> {e.excerpt}",
                "",
                "Transformation chain:",
            ])
            for step in e.transformations:
                lines.append(f"- {step.kind} via {step.tool} {step.tool_version or ''} — output `{step.output_hash or 'n/a'}`")
            if a.support_pass.fit:
                lines.append("")
                lines.append("Historical Claim Fit:")
                for d in a.support_pass.fit.dimensions:
                    lines.append(f"- **{d.dimension}**: `{d.label.value}` — {d.rationale}")
            lines.append("")
        if a.limitation_pass.evidence:
            lines.append("**Limitation/conflict candidates:**")
            for e in a.limitation_pass.evidence:
                lines.append(f"- {e.source_title}, p. {e.page_number}, score {e.score:.3f}: {e.excerpt}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
