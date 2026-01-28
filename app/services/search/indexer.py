from __future__ import annotations

import re
from dataclasses import dataclass

import pymorphy2
from rank_bm25 import BM25Okapi
from rapidfuzz import process

morph = pymorphy2.MorphAnalyzer()


def tokenize(text: str) -> list[str]:
    words = re.findall(r"\w+", text.lower())
    return [morph.parse(word)[0].normal_form for word in words]


@dataclass
class SearchResult:
    item_id: int
    score: float
    title: str


class SearchIndex:
    def __init__(self) -> None:
        self.documents: list[list[str]] = []
        self.items: list[tuple[int, str]] = []
        self.bm25: BM25Okapi | None = None

    def build(self, items: list[tuple[int, str]]) -> None:
        self.items = items
        self.documents = [tokenize(text) for _, text in items]
        self.bm25 = BM25Okapi(self.documents) if self.documents else None

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        if not self.bm25:
            return []
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:limit]
        results = [SearchResult(self.items[idx][0], float(score), self.items[idx][1]) for idx, score in ranked]
        if results:
            return results
        fuzzy = process.extract(query, [title for _, title in self.items], limit=limit, score_cutoff=60)
        return [SearchResult(self.items[idx][0], score, self.items[idx][1]) for idx, score, _ in fuzzy]
