from __future__ import annotations

import re
from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .domain import EvidenceSnippet, SourcePage
from .util import normalize_text


def _sentence_units(pages: Sequence[SourcePage]) -> List[Tuple[SourcePage, str]]:
    units: List[Tuple[SourcePage, str]] = []
    for page in pages:
        chunks = re.split(r"(?<=[.!?;:])\s+|\n+", page.text)
        for chunk in chunks:
            chunk = normalize_text(chunk)
            if len(chunk) >= 25:
                units.append((page, chunk))
    return units


class TfidfEvidenceRetriever:
    """Deterministic local retriever. No network or model call is made."""

    def __init__(self, pages: Sequence[SourcePage]):
        self.units = _sentence_units(pages)
        self.vectorizer = None
        self.matrix = None
        if self.units:
            texts = [text for _, text in self.units]
            self.vectorizer = TfidfVectorizer(
                lowercase=True, analyzer="char_wb", ngram_range=(3, 5),
                min_df=1, max_features=120000,
            )
            self.matrix = self.vectorizer.fit_transform(texts)

    def retrieve(self, claim: str, top_k: int = 5) -> List[EvidenceSnippet]:
        if not self.units or self.vectorizer is None or self.matrix is None:
            return []
        vec = self.vectorizer.transform([claim])
        sims = cosine_similarity(vec, self.matrix).ravel()
        order = np.argsort(sims)[::-1][:max(1, top_k)]
        out: List[EvidenceSnippet] = []
        for idx in order:
            page, text = self.units[int(idx)]
            out.append(EvidenceSnippet(
                source_id=page.source_id, source_title=page.source_title,
                page_number=page.page_number, score=float(sims[int(idx)]),
                excerpt=text[:700], text_sha256=page.text_sha256,
                transformations=list(page.transformations),
            ))
        return out
