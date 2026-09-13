# Benchmark strategy

The built-in benchmark is deliberately small and deterministic. It checks architectural guardrails, not live historical-research accuracy.

Current fixtures test:

1. exact support candidate;
2. support plus an independently retrieved competing date;
3. metadata-only refusal;
4. polarity/negation conflict.

For the Catalyst pilot, the benchmark should be expanded to a human-labelled corpus covering at least:

- direct support;
- metadata-only references;
- partial scans;
- OCR errors;
- transcription uncertainty;
- translation-mediated evidence;
- competing dates/numbers;
- conflicting editions;
- indirect quotation chains;
- causal overstatement;
- certainty inflation;
- source-voice ambiguity.

Recommended primary metrics:

- false full-text verification rate;
- source-state classification accuracy;
- page/passage locator accuracy;
- conflict/limitation recall on labelled cases;
- transformation-lineage integrity;
- unsupported automated revision rate (when revision is added);
- appropriate human-escalation rate;
- time and compute cost per audited claim.

No benchmark result should be reported as product accuracy unless the cases, labels, inclusion criteria, and human adjudication procedure are documented.
