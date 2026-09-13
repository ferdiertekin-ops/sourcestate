# SourceState Trust Model

## Threats the prototype is designed to resist

### 1. Metadata laundering
A bibliographic record is accidentally or deliberately treated as if the underlying source text had been inspected.

**Control:** metadata-only records are structurally excluded from content evidence. Claims that explicitly invoke such a source are blocked.

### 2. Partial-file laundering
One readable page causes a partly unreadable scan to be described as full text.

**Control:** access state is calculated from page coverage; incomplete text layers remain `partial_text`.

### 3. Transformation laundering
OCR, transcription, or translation is presented as if it were the original source wording.

**Control:** each derived text carries an append-only transformation chain with input/output hashes.

### 4. Confirmation bias in retrieval
A supporting passage is found and contrary passages are ignored.

**Control:** support and limitation passes receive the same candidate pool but run independently.

### 5. Automated overclaiming
A similarity score is transformed into a scholarly conclusion.

**Control:** machine states are explicitly labelled candidates; human review remains required.

### 6. Silent model substitution
A future LLM integration bypasses the deterministic policy layer.

**Control:** model integrations live behind an adapter boundary and receive only policy-cleared evidence.

## What SourceState does not guarantee

SourceState cannot establish historical truth by itself. It does not guarantee that an uploaded file is authentic, complete, correctly catalogued, or the authoritative edition. It records the state of the evidence supplied to the system and makes that state auditable.
