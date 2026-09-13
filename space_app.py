from __future__ import annotations

import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd

from sourcestate.benchmark import run_benchmark
from sourcestate.claims import extract_claim_candidates
from sourcestate.ingest import parse_metadata_lines, read_pdf
from sourcestate.receipt import write_audit_json, write_ledger_csv, write_research_receipt
from sourcestate.workflow import AuditEngine, VERSION
from sourcestate.domain import AuditMode

HERE = Path(__file__).resolve().parent
DEMO = HERE / "demo_data"


def _tables(session):
    claim_rows = []
    for a in session.assessments:
        support = a.support_pass.evidence[0] if a.support_pass.evidence else None
        limitation = a.limitation_pass.evidence[0] if a.limitation_pass.evidence else None
        claim_rows.append({
            "Claim": a.claim.text,
            "Status": a.status.value,
            "Support source": support.source_title if support else "—",
            "Support page": support.page_number if support else "—",
            "Limitation source": limitation.source_title if limitation else "—",
            "Human decision": a.human_decision.value,
            "Rationale": a.rationale,
        })
    source_rows = [{
        "Title": s.title,
        "Access state": s.access_state.value,
        "Inspectable pages": f"{s.pages_with_text}/{s.pages_total}" if s.pages_total else "—",
        "SHA-256": s.file_sha256 or "—",
        "Policy note": s.note,
    } for s in session.sources]
    return pd.DataFrame(claim_rows), pd.DataFrame(source_rows)


def run_demo():
    draft = (DEMO / "demo_draft.txt").read_text(encoding="utf-8")
    claims = extract_claim_candidates(draft)
    sources, pages, events, warnings = [], [], [], []
    for name in ("demo_source_alpha.pdf", "demo_source_beta.pdf"):
        rec, pgs, evs, warns = read_pdf(str(DEMO / name), False, "eng")
        sources.append(rec)
        pages.extend(pgs)
        events.extend(evs)
        warnings.extend(warns)
    sources.extend(parse_metadata_lines((DEMO / "metadata_only.txt").read_text(encoding="utf-8")))

    session = AuditEngine().run(draft, claims, sources, pages, AuditMode.DEMO, events, warnings)
    claim_df, source_df = _tables(session)
    tmp = Path(tempfile.mkdtemp(prefix="sourcestate_demo_"))
    audit = write_audit_json(session, tmp / "sourcestate_demo_audit.json")
    ledger = write_ledger_csv(session, tmp / "sourcestate_demo_ledger.csv")
    receipt = write_research_receipt(session, tmp / "sourcestate_demo_receipt.md")
    counts = claim_df["Status"].value_counts().to_dict() if not claim_df.empty else {}
    summary = (
        f"### SourceState v{VERSION} — synthetic grant demo\n"
        f"Status counts: `{counts}`.  \n"
        "The fixtures are synthetic. The demo demonstrates source-state refusal, independent support/limitation review, and auditable outputs—not historical accuracy."
    )
    return claim_df, source_df, summary, audit, ledger, receipt


def benchmark_report():
    result = run_benchmark()
    lines = [f"### Deterministic guardrail benchmark: {result['correct']}/{result['cases']} expected outcomes matched"]
    for item in result["details"]:
        mark = "PASS" if item["pass"] else "FAIL"
        lines.append(f"- **{mark}** `{item['case']}` — expected `{item['expected']}`, actual `{item['actual']}`")
    lines.append("\nThis validates deterministic guardrails only; it is not a domain-scale accuracy claim.")
    return "\n".join(lines)


with gr.Blocks(title="SourceState — Grant Demo") as demo:
    gr.Markdown(f"""
# SourceState v{VERSION}
### Synthetic public demonstration of an auditable source-to-claim trust layer

**Core rule:** material that has not been inspected cannot be represented as content-verified.

> **Privacy note:** this public demo intentionally accepts no user document uploads. Run the local `app.py` for research-mode auditing of your own files.
""")

    with gr.Tab("Grant Demo"):
        gr.Markdown("The fixtures are synthetic and deterministic: support, competing date/conflict, and metadata-only refusal.")
        run = gr.Button("Run synthetic demo", variant="primary")
        summary = gr.Markdown()
        claims = gr.Dataframe(label="Claim–Source Ledger", interactive=False, wrap=True)
        sources = gr.Dataframe(label="Source Registry", interactive=False, wrap=True)
        with gr.Row():
            audit = gr.File(label="Audit JSON")
            ledger = gr.File(label="Ledger CSV")
            receipt = gr.File(label="Research Receipt")
        run.click(run_demo, inputs=[], outputs=[claims, sources, summary, audit, ledger, receipt])

    with gr.Tab("Architecture"):
        gr.Markdown("""
```text
claim confirmation
      ↓
source-state gate
      ↓
independent support + limitation passes
      ↓
Historical Claim Fit
      ↓
human review
      ↓
Research Receipt
```

- `metadata_only` → content verification blocked
- `file_present_unreadable` → no content evidence
- `partial_text` → inspect recorded pages only
- `full_text` → inspect supplied-file text only
- OCR/transcription/translation remain explicit transformations
- final scholarly judgment remains human
""")
        bench = gr.Button("Run deterministic benchmark")
        bench_out = gr.Markdown()
        bench.click(benchmark_report, inputs=[], outputs=[bench_out])

if __name__ == "__main__":
    demo.launch()
