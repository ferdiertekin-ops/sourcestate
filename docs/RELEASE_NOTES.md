# SourceState v0.3.0 — Release notes

This release restructures the prototype around explicit source-critical trust boundaries rather than adding a generic citation-checking layer.

## Architectural changes

- Human claim-confirmation gate before Research Mode.
- Four-state source registry: `metadata_only`, `file_present_unreadable`, `partial_text`, `full_text`.
- Exact file/text SHA-256 provenance.
- Append-only transformation lineage for OCR, transcription, translation, normalization, and manual correction.
- Independent support and limitation/conflict review passes.
- Ten-dimension Historical Claim Fit scaffold.
- Research Receipt export alongside JSON audit and CSV ledger.
- Model-agnostic `SemanticJudge` adapter boundary.
- Deterministic benchmark harness.

## Correctness fixes from v0.2

- A partly readable PDF is no longer silently promoted to full text.
- Tiny/broken text layers are no longer treated as inspectable evidence.
- Claims beginning with a historical year are no longer accidentally stripped as list numbering.
- Conflict discovery now scans the retrieved candidate set independently from the strongest supporting passage.

## Validation

- 14/14 architecture/unit tests passed.
- 4/4 deterministic benchmark fixtures matched expected guardrail outcomes.
- Built-in demo yields exactly one support candidate, one conflict candidate, and one metadata-only verification block.
- Application imports, compiles, installs locally without build isolation, and serves successfully over local HTTP.
