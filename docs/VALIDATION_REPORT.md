# SourceState v0.3 — Validation Report

Validation scope: prototype architecture and deterministic guardrails. This is **not** a domain-scale historical accuracy claim.

## Automated tests

- Architecture/unit tests: **14 passed / 14**.
- Covered behaviours include:
  - claim extraction and explicit confirmation;
  - refusal of unconfirmed Research Mode claims;
  - metadata-only verification blocking;
  - independent support and limitation passes;
  - exact support path;
  - OCR-mediated Historical Claim Fit warning;
  - partial PDF classification;
  - metadata-only Zotero import;
  - Research Receipt generation;
  - transformation-lineage immutability;
  - preservation of a genuine leading year in claim parsing;
  - rejection of tiny/broken text layers as inspectable content.

## Built-in deterministic benchmark

Expected outcomes matched: **4/4**.

- exact support → `SUPPORT CANDIDATE`;
- support plus competing date → `CONFLICT CANDIDATE`;
- metadata-only named source → `VERIFICATION BLOCKED`;
- negation conflict → `CONFLICT CANDIDATE`.

## Demo behaviour

The bundled synthetic demo produces exactly:

- 1 `SUPPORT CANDIDATE`;
- 1 `CONFLICT CANDIDATE`;
- 1 `VERIFICATION BLOCKED`.

## Runtime validation

- Python compilation: passed.
- `app.py` import: passed.
- Local Gradio HTTP startup: passed (`HTTP 200` from local server).
- Static scan found no application code importing common outbound HTTP/model clients.

## Interpretation

These results show that the prototype's refusal, provenance and workflow invariants execute as designed on the covered fixtures. They do not establish recall, precision, historical validity, OCR quality, or usability in uncontrolled research corpora. Those require the grant-stage human-labelled benchmark and researcher study described in the proposal.
