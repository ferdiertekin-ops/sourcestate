from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import List, Tuple

import fitz

from .domain import AccessState, AuditEvent, SourcePage, SourceRecord, TransformationStep
from .util import new_id, normalize_text, now_iso, sha256_file, sha256_text


def event(action: str, detail: dict) -> AuditEvent:
    return AuditEvent(new_id("evt"), now_iso(), action, detail)


def _tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_page(page: fitz.Page, lang: str) -> Tuple[str, str]:
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Optional OCR dependencies are missing (pytesseract/Pillow).") from exc
    if not _tesseract_available():
        raise RuntimeError("Tesseract executable was not found on this system.")
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    version = str(pytesseract.get_tesseract_version())
    return normalize_text(pytesseract.image_to_string(img, lang=lang)), version


MIN_INSPECTABLE_CHARS = 30


def read_pdf(path: str | Path, enable_ocr: bool = False, ocr_lang: str = "eng") -> Tuple[SourceRecord, List[SourcePage], List[AuditEvent], List[str]]:
    path = Path(path)
    file_hash = sha256_file(path)
    source_id = f"pdf:{file_hash[:16]}"
    title = path.stem.replace("_", " ")
    pages: List[SourcePage] = []
    events: List[AuditEvent] = []
    warnings: List[str] = []
    doc = fitz.open(path)
    pages_ocr = 0
    pages_with_text = 0
    try:
        total = len(doc)
        for number, page in enumerate(doc, start=1):
            raw_text = normalize_text(page.get_text("text"))
            steps: List[TransformationStep] = []
            text = raw_text
            if raw_text:
                steps.append(TransformationStep(
                    step_id=new_id("xfm"), kind="pdf_text_extraction", tool="PyMuPDF",
                    tool_version=getattr(fitz, "VersionBind", None), input_hash=file_hash,
                    output_hash=sha256_text(raw_text), parameters={"page": number}
                ))
            if len(text) < MIN_INSPECTABLE_CHARS and enable_ocr:
                try:
                    ocr_text, version = _ocr_page(page, ocr_lang)
                    if ocr_text:
                        input_hash = sha256_text(text) if text else file_hash
                        text = ocr_text
                        pages_ocr += 1
                        steps.append(TransformationStep(
                            step_id=new_id("xfm"), kind="ocr", tool="Tesseract",
                            tool_version=version, input_hash=input_hash,
                            output_hash=sha256_text(text), parameters={"page": number, "language": ocr_lang}
                        ))
                        events.append(event("ocr_applied", {"source_id": source_id, "page": number, "language": ocr_lang}))
                    else:
                        warnings.append(f"{path.name}, page {number}: OCR returned no usable text.")
                except Exception as exc:
                    warnings.append(f"{path.name}, page {number}: OCR unavailable/failed — {exc}")
            elif len(text) < MIN_INSPECTABLE_CHARS and not enable_ocr:
                warnings.append(f"{path.name}, page {number}: little/no text layer; page was not OCR-processed.")

            if len(text) >= MIN_INSPECTABLE_CHARS:
                pages_with_text += 1
                pages.append(SourcePage(
                    source_id=source_id, source_title=title, page_number=number,
                    text=text, text_sha256=sha256_text(text), transformations=steps,
                ))

        if pages_with_text == 0:
            access = AccessState.FILE_PRESENT_UNREADABLE
        elif pages_with_text == total:
            access = AccessState.FULL_TEXT
        else:
            access = AccessState.PARTIAL_TEXT

        record = SourceRecord(
            source_id=source_id, title=title, access_state=access,
            filename=path.name, file_sha256=file_hash, pages_total=total,
            pages_with_text=pages_with_text, pages_ocr=pages_ocr,
            note="Exact uploaded file hash recorded. Partial files are not represented as complete full text.",
        )
        events.append(event("source_loaded", {
            "source_id": source_id, "filename": path.name, "file_sha256": file_hash,
            "access_state": access.value, "pages_total": total,
            "pages_with_text": pages_with_text, "pages_ocr": pages_ocr,
        }))
        return record, pages, events, warnings
    finally:
        doc.close()


def parse_metadata_lines(text: str) -> List[SourceRecord]:
    records: List[SourceRecord] = []
    for idx, raw in enumerate((text or "").splitlines(), start=1):
        title = normalize_text(raw)
        if not title:
            continue
        records.append(SourceRecord(
            source_id=f"meta:manual:{idx}", title=title,
            access_state=AccessState.METADATA_ONLY,
            note="Bibliographic/metadata record only. Content verification is prohibited.",
        ))
    return records


def parse_zotero_json(path: str | Path) -> List[SourceRecord]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        items = data.get("items") or data.get("data") or [data]
    else:
        items = data
    records: List[SourceRecord] = []
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        title = normalize_text(str(item.get("title") or item.get("name") or "Untitled Zotero item"))
        key = str(item.get("key") or item.get("citationKey") or idx)
        locator = str(item.get("DOI") or item.get("doi") or item.get("url") or "") or None
        records.append(SourceRecord(
            source_id=f"meta:zotero:{key}", title=title,
            access_state=AccessState.METADATA_ONLY, locator=locator,
            note="Imported from Zotero metadata. Attachment content has not been inspected.",
        ))
    return records
