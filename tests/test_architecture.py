from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from sourcestate.benchmark import run_benchmark
from sourcestate.claims import extract_claim_candidates, parse_confirmed_claim_text
from sourcestate.domain import (
    AccessState, AssessmentStatus, AuditMode, Claim, FitLabel, SourcePage, SourceRecord, TransformationStep
)
from sourcestate.fit import historical_claim_fit
from sourcestate.ingest import parse_zotero_json, read_pdf
from sourcestate.policy import can_use_content
from sourcestate.receipt import write_research_receipt
from sourcestate.util import new_id, sha256_text
from sourcestate.workflow import AuditEngine


def page(source_id, title, text, kind="pdf_text_extraction"):
    step = TransformationStep(new_id("xfm"), kind, "test", output_hash=sha256_text(text))
    return SourcePage(source_id, title, 1, text, sha256_text(text), [step])


def source(source_id, title, state=AccessState.FULL_TEXT):
    return SourceRecord(source_id, title, state, pages_total=1, pages_with_text=1 if state in {AccessState.FULL_TEXT, AccessState.PARTIAL_TEXT} else 0)


def test_claim_extraction_and_confirmation():
    draft = "The event occurred on 29 February 1880 in the capital. This second sentence is long enough to audit."
    assert len(extract_claim_candidates(draft)) == 2
    claims = parse_confirmed_claim_text("1. First historical claim with enough words.\n2. Second historical claim with enough words.")
    assert len(claims) == 2 and all(c.user_confirmed for c in claims)


def test_research_mode_refuses_unconfirmed_claim():
    engine = AuditEngine()
    with pytest.raises(ValueError):
        engine.run("draft", [Claim("C001", "An unconfirmed claim exists here.", False)], [], [], AuditMode.RESEARCH)


def test_metadata_only_never_content_verifies():
    engine = AuditEngine()
    claim = Claim("C001", "Archive Bulletin Gamma 1912 proves that the committee met in April.", True)
    session = engine.run(claim.text, [claim], [SourceRecord("m", "Archive Bulletin Gamma 1912", AccessState.METADATA_ONLY)], [], AuditMode.RESEARCH)
    assert session.assessments[0].status == AssessmentStatus.VERIFICATION_BLOCKED


def test_support_and_limitation_are_independent():
    claim = Claim("C001", "The event occurred on 29 February 1880 in the capital.", True)
    pages = [
        page("a", "Alpha", "The event occurred on 29 February 1880 in the capital."),
        page("b", "Beta", "A later memorandum dates the event to 1 March 1880 in the capital."),
    ]
    session = AuditEngine().run(claim.text, [claim], [source("a", "Alpha"), source("b", "Beta")], pages, AuditMode.RESEARCH)
    a = session.assessments[0]
    assert a.support_pass.evidence
    assert a.limitation_pass.evidence
    assert a.status == AssessmentStatus.CONFLICT_CANDIDATE


def test_exact_support_without_conflict():
    claim = Claim("C001", "The event occurred on 29 February 1880 in the capital.", True)
    pages = [page("a", "Alpha", claim.text)]
    session = AuditEngine().run(claim.text, [claim], [source("a", "Alpha")], pages, AuditMode.RESEARCH)
    assert session.assessments[0].status == AssessmentStatus.SUPPORT_CANDIDATE


def test_historical_fit_flags_ocr_as_mediated():
    epage = page("a", "Alpha", "The event occurred on 29 February 1880 in the capital.", "ocr")
    from sourcestate.domain import EvidenceSnippet
    ev = EvidenceSnippet("a", "Alpha", 1, 0.9, epage.text, epage.text_sha256, epage.transformations)
    fit = historical_claim_fit(epage.text, ev)
    transform = next(d for d in fit.dimensions if d.dimension == "transformation_state")
    assert transform.label == FitLabel.PARTIAL


def test_partial_pdf_is_not_upgraded_to_full_text(tmp_path):
    pdf = tmp_path / "partial.pdf"
    doc = fitz.open()
    p1 = doc.new_page(); p1.insert_text((72, 72), "This page contains enough extractable text to count as readable for the source audit.")
    doc.new_page()
    doc.save(pdf); doc.close()
    rec, pages, events, warnings = read_pdf(pdf, enable_ocr=False)
    assert rec.access_state == AccessState.PARTIAL_TEXT
    assert rec.pages_with_text == 1 and rec.pages_total == 2


def test_full_text_policy():
    assert can_use_content(source("a", "Alpha", AccessState.FULL_TEXT))
    assert can_use_content(source("p", "Partial", AccessState.PARTIAL_TEXT))
    assert not can_use_content(SourceRecord("m", "Meta", AccessState.METADATA_ONLY))


def test_zotero_remains_metadata_only(tmp_path):
    path = tmp_path / "zotero.json"
    path.write_text(json.dumps([{"key": "X", "title": "Article", "DOI": "10.1/x"}]), encoding="utf-8")
    records = parse_zotero_json(path)
    assert records[0].access_state == AccessState.METADATA_ONLY
    assert records[0].locator == "10.1/x"


def test_research_receipt_records_source_state_and_claim(tmp_path):
    claim = Claim("C001", "The event occurred on 29 February 1880 in the capital.", True)
    pages = [page("a", "Alpha", claim.text)]
    session = AuditEngine().run(claim.text, [claim], [source("a", "Alpha")], pages, AuditMode.RESEARCH)
    out = Path(write_research_receipt(session, tmp_path / "receipt.md"))
    text = out.read_text(encoding="utf-8")
    assert "Access state" in text and "C001" in text and "Human decision" in text


def test_builtin_benchmark_passes_all_current_fixtures():
    result = run_benchmark()
    assert result["correct"] == result["cases"]


def test_transformation_lineage_is_append_only():
    from sourcestate.transform import derive_page_text
    parent = page("a", "Alpha", "Original extracted wording.")
    derived = derive_page_text(parent, "Diplomatic transcription wording.", "transcription", "human")
    translated = derive_page_text(derived, "Modern translation wording.", "translation", "human")
    assert parent.text == "Original extracted wording."
    assert len(parent.transformations) == 1
    assert len(derived.transformations) == 2
    assert len(translated.transformations) == 3
    assert derived.transformations[-1].input_hash == parent.text_sha256
    assert translated.transformations[-1].input_hash == derived.text_sha256


def test_claim_parser_does_not_strip_historical_year():
    claims = parse_confirmed_claim_text("1880 was a consequential year for this historical episode.")
    assert claims[0].text.startswith("1880")


def test_tiny_broken_text_layer_is_not_inspectable(tmp_path):
    pdf = tmp_path / "tiny.pdf"
    doc = fitz.open(); p = doc.new_page(); p.insert_text((72, 72), "x"); doc.save(pdf); doc.close()
    rec, pages, events, warnings = read_pdf(pdf, enable_ocr=False)
    assert rec.access_state == AccessState.FILE_PRESENT_UNREADABLE
    assert rec.pages_with_text == 0
    assert pages == []
