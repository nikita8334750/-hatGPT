from __future__ import annotations

import math
import re
from collections import Counter

import networkx as nx


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s]


def sentence_similarity(a: str, b: str) -> float:
    words_a = Counter(re.findall(r"\w+", a.lower()))
    words_b = Counter(re.findall(r"\w+", b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = set(words_a) & set(words_b)
    numerator = sum(words_a[w] * words_b[w] for w in intersection)
    denominator = math.sqrt(sum(v * v for v in words_a.values())) * math.sqrt(
        sum(v * v for v in words_b.values())
    )
    return numerator / denominator if denominator else 0.0


def summarize(text: str, max_sentences: int = 5) -> list[str]:
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return sentences
    graph = nx.Graph()
    for i, sent in enumerate(sentences):
        graph.add_node(i, sentence=sent)
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            similarity = sentence_similarity(sentences[i], sentences[j])
            if similarity > 0:
                graph.add_edge(i, j, weight=similarity)
    scores = nx.pagerank(graph, weight="weight")
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_indices = sorted([idx for idx, _ in ranked[:max_sentences]])
    return [sentences[idx] for idx in top_indices]
