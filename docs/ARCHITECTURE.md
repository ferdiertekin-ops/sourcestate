# SourceState v0.3 — Architecture

## 1. Design objective

SourceState is not a truth engine. It is an auditable source-to-claim control layer for research. Its first obligation is to preserve the epistemic status of evidence: what was actually available, in what form, after which transformations, and where human judgment remains necessary.

## 2. Non-negotiable invariants

1. **No unseen-source verification.** Metadata, catalogue records, abstracts, snippets, and bibliographic references cannot become content evidence by implication.
2. **No silent completeness upgrade.** A partly readable file remains `partial_text`; it is never labelled `full_text` merely because some pages are readable.
3. **Transformation lineage is append-only.** OCR, transcription, translation, normalization, and correction create derived artifacts. They never overwrite the provenance of the parent text.
4. **Claims are human-confirmed before Research Mode.** Machine extraction proposes units of audit; the researcher decides what the actual claim is.
5. **Support and limitation reviews are independent.** A strong supporting passage cannot suppress a competing date, number, polarity, or other limiting signal found elsewhere in the supplied corpus.
6. **Machine labels are provisional.** `SUPPORT CANDIDATE`, `CONFLICT CANDIDATE`, and related states are retrieval/audit signals, not historical verdicts.
7. **Every research session emits a receipt.** File hashes, access states, passages, page locators, transformations, machine decisions, and pending human decisions are exportable.

## 3. Layered architecture

```text
User draft
   │
   ▼
Claim Extraction ──► Human Claim Confirmation Gate
   │
   ▼
Source Registry ───► Source-State Policy Gate
   │                      │
   │                      ├─ metadata_only ──► CONTENT VERIFICATION BLOCKED
   │                      ├─ unreadable ─────► NO CONTENT EVIDENCE
   │                      ├─ partial_text ───► inspect only recorded pages
   │                      └─ full_text ──────► inspect recorded pages
   ▼
Evidence Retrieval (deterministic local baseline)
   │
   ├─────────────────────────────┐
   ▼                             ▼
Support Review Pass        Limitation Review Pass
(independent)              (independent)
   │                             │
   └──────────────┬──────────────┘
                  ▼
Historical Claim Fit
                  │
                  ▼
Provisional Assessment
                  │
                  ▼
Human Historian Review
                  │
                  ▼
Research Receipt + Audit JSON + Ledger CSV
```

## 4. Domain model

### Source state

`metadata_only` → title/DOI/catalogue information may be recorded, but content claims are prohibited.

`file_present_unreadable` → the exact file exists and is hashed, but no usable text was extracted.

`partial_text` → some pages are inspectable and some are not; only inspectable pages may enter retrieval.

`full_text` → all pages in the supplied file produced inspectable text. This means *full text of the supplied file*, not a guarantee that the file itself is a complete/canonical edition.

### Transformation lineage

A source page carries an ordered chain of `TransformationStep` records. Each step records:

- transformation kind;
- tool and version where available;
- parameters;
- input hash;
- output hash.

Example:

```text
PDF file SHA-256
  └─ pdf_text_extraction → text hash A
        └─ manual_correction → text hash B
              └─ transcription → text hash C
                    └─ translation → text hash D
```

The parent remains intact at every stage.

## 5. Historical Claim Fit

The deterministic v0.3 baseline surfaces ten dimensions rather than pretending to solve them all automatically:

1. date/time and quantity;
2. polarity/negation;
3. actors, institutions, places (surface heuristic only);
4. causality/intent;
5. certainty strength;
6. transformation state;
7. source voice;
8. genre/document function;
9. edition/version;
10. direct vs indirect derivation.

Dimensions 7–10 intentionally remain `unknown` unless explicit evidence exists. This is a feature: the architecture represents unresolved source-critical questions instead of fabricating answers.

## 6. Agent/model boundary

v0.3 ships no network model dependency. A future `SemanticJudge` adapter can use an LLM or local NLI model, but it must receive only policy-cleared evidence and return structured assessments. It may not bypass source-state policy, rewrite provenance, or convert metadata into full-text evidence.

This keeps the trust layer independent from model vendor and model generation.

## 7. Data outputs

Each audit emits three artifacts:

- `sourcestate_audit.json` — machine-readable full session, source registry, events, assessments and policy;
- `claim_source_ledger.csv` — compact claim-by-claim audit table;
- `research_receipt.md` — human-readable source registry, evidence passages, transformations and Historical Claim Fit.

## 8. Current limitations

- Claim extraction is sentence-based and deterministic; atomic decomposition is not yet semantic.
- Retrieval uses TF-IDF rather than embeddings.
- Proper-name comparison is a conservative surface heuristic, not NER.
- Historical Claim Fit does not automatically determine source voice, genre, edition identity, or indirect derivation.
- OCR requires local Tesseract and remains unverified until checked against the image.
- No external literature or archive service is queried silently.

These limitations are explicit so the prototype demonstrates refusal and provenance behaviour rather than overstating research intelligence.
