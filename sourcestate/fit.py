from __future__ import annotations

import re
from typing import List, Optional, Set

from .domain import DimensionAssessment, EvidenceSnippet, FitLabel, HistoricalClaimFit

NEGATIONS = {"not", "no", "never", "without", "neither", "nor", "değil", "yok", "hiç", "olmadı", "olmamıştır", "bulunmadı"}
CAUSAL = {"because", "caused", "resulted", "therefore", "due", "nedeniyle", "sebebiyle", "sonucunda", "yol açtı", "dolayı"}
CERTAINTY_STRONG = {"certainly", "definitely", "proved", "proves", "kesin", "kesinlikle", "kanıtlar", "ispatlar"}
CERTAINTY_WEAK = {"possibly", "probably", "appears", "suggests", "muhtemel", "muhtemelen", "görünmektedir", "düşündürmektedir"}
MONTHS = {"january","february","march","april","may","june","july","august","september","october","november","december","ocak","şubat","mart","nisan","mayıs","haziran","temmuz","ağustos","eylül","ekim","kasım","aralık"}


def _tokens(text: str) -> Set[str]:
    return {t.lower() for t in re.findall(r"[\w’'-]+", text, flags=re.UNICODE) if len(t) > 2}


def _numbers(text: str) -> Set[str]:
    return set(re.findall(r"\b\d{1,4}\b", text))


def _has_any(text: str, words: Set[str]) -> bool:
    low = text.lower()
    return any(word in low for word in words)


def _dateish(text: str) -> bool:
    toks = _tokens(text)
    return bool(toks & MONTHS) or bool(re.search(r"\b(?:18|19|20)\d{2}\b", text))


def _properish(text: str) -> Set[str]:
    # Conservative surface heuristic, not named-entity recognition.
    return {m.group(0).lower() for m in re.finditer(r"\b[A-ZÇĞİÖŞÜ][\w’'-]{2,}\b", text)}


def historical_claim_fit(claim: str, evidence: EvidenceSnippet) -> HistoricalClaimFit:
    ev = evidence.excerpt
    dims: List[DimensionAssessment] = []

    claim_nums, ev_nums = _numbers(claim), _numbers(ev)
    if claim_nums and ev_nums:
        if _dateish(claim) or _dateish(ev):
            label = FitLabel.MATCH if claim_nums == ev_nums else (FitLabel.CONFLICT if claim_nums & ev_nums else FitLabel.PARTIAL)
            rationale = f"Claim numbers={sorted(claim_nums)}; evidence numbers={sorted(ev_nums)}."
        else:
            label = FitLabel.MATCH if claim_nums == ev_nums else FitLabel.PARTIAL
            rationale = f"Quantities differ or only partly overlap: {sorted(claim_nums)} vs {sorted(ev_nums)}."
    else:
        label, rationale = FitLabel.UNKNOWN, "No robust date/number comparison available."
    dims.append(DimensionAssessment("date_time_and_quantity", label, rationale))

    cneg, eneg = bool(_tokens(claim) & NEGATIONS), bool(_tokens(ev) & NEGATIONS)
    if cneg != eneg:
        lexical = (_tokens(claim) - NEGATIONS) & (_tokens(ev) - NEGATIONS)
        label = FitLabel.CONFLICT if len(lexical) >= 2 else FitLabel.UNKNOWN
        rationale = "Potential polarity mismatch." if label == FitLabel.CONFLICT else "Negation differs but lexical overlap is insufficient for a conflict finding."
    else:
        label, rationale = FitLabel.MATCH, "No polarity mismatch detected by deterministic rules."
    dims.append(DimensionAssessment("polarity", label, rationale))

    cp, ep = _properish(claim), _properish(ev)
    if cp and ep:
        overlap = cp & ep
        label = FitLabel.MATCH if overlap == cp else (FitLabel.PARTIAL if overlap else FitLabel.UNKNOWN)
        rationale = f"Surface proper-name overlap: {sorted(overlap)}."
    else:
        label, rationale = FitLabel.UNKNOWN, "Proper-name comparison unavailable or inconclusive."
    dims.append(DimensionAssessment("actors_institutions_places", label, rationale))

    claim_causal = _has_any(claim, CAUSAL)
    ev_causal = _has_any(ev, CAUSAL)
    if claim_causal and not ev_causal:
        label, rationale = FitLabel.PARTIAL, "The claim contains causal language not mirrored in the retrieved passage."
    elif claim_causal and ev_causal:
        label, rationale = FitLabel.MATCH, "Both claim and evidence contain causal language; human review must assess actual causation."
    else:
        label, rationale = FitLabel.NOT_APPLICABLE, "No explicit causal formulation detected in the claim."
    dims.append(DimensionAssessment("causality_intent", label, rationale))

    claim_strong, ev_strong = _has_any(claim, CERTAINTY_STRONG), _has_any(ev, CERTAINTY_STRONG)
    claim_weak, ev_weak = _has_any(claim, CERTAINTY_WEAK), _has_any(ev, CERTAINTY_WEAK)
    if claim_strong and ev_weak:
        label, rationale = FitLabel.PARTIAL, "Claim certainty appears stronger than the retrieved passage."
    elif claim_weak and ev_strong:
        label, rationale = FitLabel.MATCH, "Claim is no stronger than the retrieved passage by surface certainty markers."
    else:
        label, rationale = FitLabel.UNKNOWN, "Certainty comparison is not decisive by deterministic rules."
    dims.append(DimensionAssessment("certainty_strength", label, rationale))

    kinds = [step.kind for step in evidence.transformations]
    if "ocr" in kinds or "translation" in kinds or "transcription" in kinds:
        label = FitLabel.PARTIAL
        rationale = f"Evidence passes through mediated transformation(s): {kinds}; original image/text should be checked."
    else:
        label = FitLabel.MATCH
        rationale = f"Recorded transformation chain: {kinds or ['none recorded']}."
    dims.append(DimensionAssessment("transformation_state", label, rationale))

    dims.extend([
        DimensionAssessment("source_voice", FitLabel.UNKNOWN, "Who is speaking/recording must be established by source criticism."),
        DimensionAssessment("genre_and_document_function", FitLabel.UNKNOWN, "Document genre/function is not inferred automatically in v0.3."),
        DimensionAssessment("edition_or_version", FitLabel.UNKNOWN, "Edition/version identity requires explicit metadata or human review."),
        DimensionAssessment("direct_vs_indirect_derivation", FitLabel.UNKNOWN, "Indirect quotation/derivation requires citation-chain data or human review."),
    ])
    return HistoricalClaimFit(dims)


def hard_conflict_reason(claim: str, evidence: str, score: float, min_similarity: float = 0.20) -> Optional[str]:
    if score < min_similarity:
        return None
    cnums, enums = _numbers(claim), _numbers(evidence)
    if cnums and enums and cnums != enums and (_dateish(claim) or _dateish(evidence)):
        if cnums & enums:
            return "Potential date/number mismatch in a closely related passage."
    cneg, eneg = bool(_tokens(claim) & NEGATIONS), bool(_tokens(evidence) & NEGATIONS)
    if cneg != eneg:
        overlap = len((_tokens(claim) - NEGATIONS) & (_tokens(evidence) - NEGATIONS))
        if overlap >= 2:
            return "Potential polarity/negation mismatch in a closely related passage."
    return None
