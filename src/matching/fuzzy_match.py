from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from src.matching.normalize import normalize_text


@dataclass
class FuzzyMatch:
    score: float
    snippet: str
    exact: bool


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() * 100


def match_query(text: str, query: str) -> FuzzyMatch:
    norm_text = normalize_text(text)
    norm_query = normalize_text(query)

    if not norm_text or not norm_query:
        return FuzzyMatch(score=0.0, snippet="", exact=False)

    if norm_query in norm_text:
        return FuzzyMatch(score=100.0, snippet=extract_snippet(text, query), exact=True)

    token_score = _ratio(norm_query, norm_text)
    partial_score = max((_ratio(norm_query, token) for token in norm_text.split()), default=0.0)
    score = max(token_score, partial_score)
    return FuzzyMatch(score=score, snippet=extract_snippet(text, query), exact=False)


def extract_snippet(text: str, query: str, span: int = 35) -> str:
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[: span * 2]
    start = max(idx - span, 0)
    end = min(idx + len(query) + span, len(text))
    return text[start:end]
