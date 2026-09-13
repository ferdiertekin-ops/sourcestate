from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

import gradio as gr
import pandas as pd

from sourcestate.benchmark import run_benchmark
from sourcestate.claims import extract_claim_candidates, parse_confirmed_claim_text
from sourcestate.domain import AuditMode
from sourcestate.ingest import parse_metadata_lines, parse_zotero_json, read_pdf
from sourcestate.receipt import write_audit_json, write_ledger_csv, write_research_receipt
from sourcestate.workflow import AuditEngine, VERSION

HERE = Path(__file__).resolve().parent
DEMO = HERE / "demo_data"


def prepare_claims(draft: str):
    claims = extract_claim_candidates(draft or "")
    if not claims:
        return "", "No declarative claim candidates found."
    text = "\n".join(f"{i}. {claim}" for i, claim in enumerate(claims, start=1))
    return text, f"Extracted **{len(claims)}** candidate claims. Edit them if needed, then explicitly confirm before auditing."


def _tables(session):
    claim_rows = []
    for a in session.assessments:
        support = a.support_pass.evidence[0] if a.support_pass.evidence else None
        limitation = a.limitation_pass.evidence[0] if a.limitation_pass.evidence else None
        fit_conflicts = a.support_pass.fit.conflicts if a.support_pass.fit else 0
        fit_partials = a.support_pass.fit.partials if a.support_pass.fit else 0
        claim_rows.append({
            "Claim ID": a.claim.claim_id,
            "Claim": a.claim.text,
            "Status": a.status.value,
            "Support source": support.source_title if support else "—",
            "Support page": support.page_number if support else "—",
            "Support score": round(support.score, 3) if support else 0.0,
            "Limitation source": limitation.source_title if limitation else "—",
            "Fit conflicts": fit_conflicts,
            "Fit partials": fit_partials,
            "Human decision": a.human_decision.value,
            "Rationale": a.rationale,
        })
    source_rows = [{
        "Source ID": s.source_id,
        "Title": s.title,
        "Access state": s.access_state.value,
        "Filename": s.filename or "—",
        "Inspectable pages": f"{s.pages_with_text}/{s.pages_total}" if s.pages_total else "—",
        "OCR pages": s.pages_ocr,
        "SHA-256": s.file_sha256 or "—",
        "Locator": s.locator or "—",
        "Policy note": s.note,
    } for s in session.sources]
    return pd.DataFrame(claim_rows), pd.DataFrame(source_rows)


def _outputs(session):
    tmp = Path(tempfile.mkdtemp(prefix="sourcestate_v03_"))
    audit = write_audit_json(session, tmp / "sourcestate_audit.json")
    ledger = write_ledger_csv(session, tmp / "claim_source_ledger.csv")
    receipt = write_research_receipt(session, tmp / "research_receipt.md")
    claim_df, source_df = _tables(session)
    return claim_df, source_df, audit, ledger, receipt


def run_audit(draft, confirmed_text, confirmed_checkbox, pdf_files, metadata_text, zotero_file, enable_ocr, ocr_lang):
    if not confirmed_checkbox:
        return pd.DataFrame(), pd.DataFrame(), "**Audit stopped:** claims must be reviewed and confirmed first.", None, None, None
    claims = parse_confirmed_claim_text(confirmed_text or "")
    if not claims:
        return pd.DataFrame(), pd.DataFrame(), "**Audit stopped:** no confirmed claims are present.", None, None, None

    sources, pages, events, warnings = [], [], [], []
    for f in pdf_files or []:
        path = getattr(f, "name", None) or str(f)
        try:
            rec, pgs, evs, warns = read_pdf(path, bool(enable_ocr), (ocr_lang or "eng").strip())
            sources.append(rec); pages.extend(pgs); events.extend(evs); warnings.extend(warns)
        except Exception as exc:
            warnings.append(f"Could not read {Path(path).name}: {exc}")

    sources.extend(parse_metadata_lines(metadata_text or ""))
    if zotero_file:
        zpath = getattr(zotero_file, "name", None) or str(zotero_file)
        try:
            sources.extend(parse_zotero_json(zpath))
        except Exception as exc:
            warnings.append(f"Zotero JSON could not be parsed: {exc}")

    engine = AuditEngine()
    session = engine.run(draft or "", claims, sources, pages, AuditMode.RESEARCH, events, warnings)
    claim_df, source_df, audit, ledger, receipt = _outputs(session)
    counts = claim_df["Status"].value_counts().to_dict() if not claim_df.empty else {}
    summary = (
        f"### Research audit complete — SourceState v{VERSION}\n"
        f"**{len(claims)}** confirmed claims; **{len(pages)}** inspectable pages; **{len(sources)}** source records.  \n"
        f"Status counts: `{counts}`.  \n"
        "Support and limitation passes were run independently. Metadata-only sources were not used as content evidence.  \n"
        "**All machine labels remain provisional until historian review.**"
    )
    if warnings:
        summary += "\n\nWarnings: " + " | ".join(warnings[:8])
    return claim_df, source_df, summary, audit, ledger, receipt


def run_demo():
    draft = (DEMO / "demo_draft.txt").read_text(encoding="utf-8")
    prepared, _ = prepare_claims(draft)
    pdfs = [str(DEMO / "demo_source_alpha.pdf"), str(DEMO / "demo_source_beta.pdf")]
    metadata = (DEMO / "metadata_only.txt").read_text(encoding="utf-8")
    return run_audit(draft, prepared, True, pdfs, metadata, None, False, "eng")


def benchmark_report():
    result = run_benchmark()
    lines = [f"### Built-in deterministic benchmark: {result['correct']}/{result['cases']} expected outcomes matched"]
    for item in result["details"]:
        mark = "PASS" if item["pass"] else "FAIL"
        lines.append(f"- **{mark}** `{item['case']}` — expected `{item['expected']}`, actual `{item['actual']}`")
    lines.append("\nThis benchmark validates deterministic guardrails only; it is not a claim of live historical-research accuracy.")
    return "\n".join(lines)


with gr.Blocks(title="SourceState — Auditable Source-to-Claim Research") as demo:
    gr.Markdown(f"""
# SourceState v{VERSION}
### Auditable source-to-claim research for humanities and social sciences

**Non-negotiable rule:** material that has not been inspected cannot be represented as content-verified.  
**Architecture:** claim confirmation → source-state gate → independent support / limitation passes → Historical Claim Fit → human review → Research Receipt.
""")

    with gr.Tab("Research Mode"):
        draft = gr.Textbox(label="1. Draft paragraph", lines=10, placeholder="Paste a research paragraph…")
        prepare = gr.Button("Extract claim candidates")
        claim_note = gr.Markdown()
        confirmed_text = gr.Textbox(label="2. Review/edit atomic claims (one per line)", lines=10)
        confirm = gr.Checkbox(label="I reviewed these claims and confirm them for audit", value=False)
        prepare.click(prepare_claims, inputs=[draft], outputs=[confirmed_text, claim_note])

        with gr.Row():
            pdf_files = gr.File(label="3. Inspectable PDFs", file_types=[".pdf"], file_count="multiple")
            with gr.Column():
                metadata_text = gr.Textbox(label="4. Metadata-only sources (one per line)", lines=5)
                zotero_file = gr.File(label="5. Optional Zotero JSON (metadata only)", file_types=[".json"], file_count="single")
                enable_ocr = gr.Checkbox(label="Optional local Tesseract OCR for missing text layers", value=False)
                ocr_lang = gr.Textbox(label="Tesseract language code", value="eng")
        run = gr.Button("Run source-state audit", variant="primary")
        summary = gr.Markdown()
        claim_table = gr.Dataframe(label="Claim–Source Ledger", interactive=False, wrap=True)
        source_table = gr.Dataframe(label="Source Registry", interactive=False, wrap=True)
        with gr.Row():
            audit_json = gr.File(label="Audit JSON")
            ledger_csv = gr.File(label="Ledger CSV")
            receipt_md = gr.File(label="Research Receipt")
        run.click(
            run_audit,
            inputs=[draft, confirmed_text, confirm, pdf_files, metadata_text, zotero_file, enable_ocr, ocr_lang],
            outputs=[claim_table, source_table, summary, audit_json, ledger_csv, receipt_md],
        )

    with gr.Tab("Demo Mode"):
        gr.Markdown("Synthetic, deterministic demonstration. It includes a support case, a competing-date case, and a metadata-only refusal case.")
        demo_run = gr.Button("Run built-in demo", variant="primary")
        d_summary = gr.Markdown()
        d_claims = gr.Dataframe(label="Demo Claim–Source Ledger", interactive=False, wrap=True)
        d_sources = gr.Dataframe(label="Demo Source Registry", interactive=False, wrap=True)
        with gr.Row():
            d_json = gr.File(label="Demo Audit JSON")
            d_csv = gr.File(label="Demo Ledger")
            d_receipt = gr.File(label="Demo Research Receipt")
        demo_run.click(run_demo, inputs=[], outputs=[d_claims, d_sources, d_summary, d_json, d_csv, d_receipt])

    with gr.Tab("Architecture & Benchmark"):
        gr.Markdown("""
## Trust boundaries
- Metadata, abstracts, snippets, and bibliographic records never become full-text evidence by implication.
- Partial PDFs remain `partial_text`; one readable page does not silently upgrade a file to `full_text`.
- OCR is recorded as a transformation. OCR text is never represented as identical to the original image.
- Research-mode claims must be reviewed and confirmed before the audit runs.
- Support and limitation passes are independent. A supporting passage cannot hide a conflicting retrieved passage.
- Historical Claim Fit exposes dimensions the machine can compare and leaves source voice, genre, edition, and indirect derivation explicitly unresolved when data are absent.
- Final scholarly judgment remains human.
""")
        bench = gr.Button("Run deterministic benchmark")
        bench_out = gr.Markdown()
        bench.click(benchmark_report, inputs=[], outputs=[bench_out])

if __name__ == "__main__":
    demo.launch(inbrowser=True)
