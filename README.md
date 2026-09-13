# SourceState

**Auditable source-to-claim provenance for AI-assisted research in the humanities and social sciences.**

SourceState is a research prototype built around one non-negotiable rule:

> **Material that has not been inspected cannot be represented as content-verified.**

Modern research workflows often flatten materially different states—full text, partial text, metadata, OCR, transcription, translation, and indirect citation—into the same fluent answer. SourceState keeps those states explicit and auditable.

## What the prototype demonstrates

- Four explicit source-access states: `metadata_only`, `file_present_unreadable`, `partial_text`, `full_text`.
- Exact SHA-256 fingerprints for supplied files and derived text.
- Append-only transformation lineage for PDF extraction, OCR/HTR, manual correction, transcription, and translation.
- Human confirmation of claim units before research-mode auditing.
- Independent **support** and **limitation/conflict** review passes.
- Page- and sentence-level evidence candidates.
- Historical Claim Fit dimensions that surface rather than hide unresolved source-critical questions.
- Zotero JSON import as metadata only unless content is separately supplied.
- A claim–source ledger, machine-readable audit JSON, and human-readable Research Receipt.
- No silent web or LLM calls in v0.3.

Machine labels are **provisional research-audit signals**, not declarations of historical truth.

## 90-second demo path

1. Launch the app.
2. Open **Demo Mode**.
3. Click **Run built-in demo**.
4. Inspect three deterministic behaviours:
   - a support candidate;
   - a competing-date/conflict candidate;
   - a metadata-only source that returns `VERIFICATION BLOCKED`.
5. Open the Research Receipt and source registry.
6. Run the deterministic benchmark under **Architecture & Benchmark**.

The demo data are synthetic and make no historical claim.

## Architecture

```text
Draft / claim candidates
        ↓
Human claim confirmation
        ↓
Source-state gate
  ├─ metadata_only ─────────→ content verification blocked
  ├─ file_present_unreadable → no content evidence
  ├─ partial_text ───────────→ inspect recorded pages only
  └─ full_text ──────────────→ inspect supplied file text
        ↓
Evidence retrieval
   ┌───────────────┴───────────────┐
   ↓                               ↓
Support review               Limitation review
(independent)                 (independent)
   └───────────────┬───────────────┘
                   ↓
          Historical Claim Fit
                   ↓
          Provisional assessment
                   ↓
           Human historian review
                   ↓
       Research Receipt + audit log
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/TRUST_MODEL.md`](docs/TRUST_MODEL.md).

## Local quick start

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The local app includes Research Mode, Demo Mode, and the benchmark view.

### Optional OCR

OCR is opt-in and requires local Tesseract plus the Python binding:

```bash
pip install -r optional_ocr_requirements.txt
```

OCR output is recorded as a transformation and is never treated as error-free transcription.

## Tests

```bash
pip install pytest
pytest -q
```

The v0.3 release validation recorded **14/14 architecture tests passing** and **4/4 expected deterministic benchmark fixtures matching**. These validate guardrails and reproducibility, not domain-scale historical-research accuracy. See [`docs/VALIDATION_REPORT.md`](docs/VALIDATION_REPORT.md).

## Public demo deployment

For a public grant demo, use the synthetic-only `space_app.py`, which intentionally disables arbitrary file uploads. A Hugging Face Spaces configuration template is provided under [`deploy/huggingface/`](deploy/huggingface/).

## Scope and current limitations

- Retrieval uses deterministic TF-IDF rather than a remote embedding or LLM service.
- Conflict detection is deliberately conservative.
- Source authenticity, archival completeness, canonical-edition status, and historical truth are not established automatically.
- OCR quality depends on the scan and local OCR engine.
- Word/Overleaf/Zotero plugins are not yet implemented; Zotero JSON is the current metadata bridge.
- Final scholarly judgment remains human.

## Project status

**v0.3.0 — working local prototype, pre-user pilot.**

SourceState is being developed as a provenance and research-integrity layer rather than a generic citation checker. Its distinctive object is the chain from **source state → transformation → evidence passage → scholarly claim**.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Trust model](docs/TRUST_MODEL.md)
- [Benchmark strategy](docs/BENCHMARK.md)
- [Validation report](docs/VALIDATION_REPORT.md)
- [Release notes](docs/RELEASE_NOTES.md)

## Author

Assoc. Prof. Dr. Ferdi Ertekin  
Department of History, Trakya University, Türkiye

## License

No open-source license has yet been granted. The code is publicly inspectable for evaluation and research discussion; reuse rights remain reserved unless a license is added later.
