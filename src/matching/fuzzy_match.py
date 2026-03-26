from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from src.matching.normalize import normalize_text


@dataclass
class FuzzyMatch:
    score: float
    snippet: str
    exact: bool
    matched_token: str = ""


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() * 100


def match_query(text: str, query: str) -> FuzzyMatch:
    norm_text = normalize_text(text)
    norm_query = normalize_text(query)

    if not norm_text or not norm_query:
        return FuzzyMatch(score=0.0, snippet="", exact=False)

    if norm_query in norm_text:
        return FuzzyMatch(score=100.0, snippet=extract_snippet(text, query), exact=True, matched_token=norm_query)

    best_token = ""
    best_score = 0.0
    tokens = norm_text.split()
    query_tokens = norm_query.split()
    window_size = max(1, len(query_tokens))

    candidates: list[str] = []
    candidates.extend(tokens)
    if 1 < window_size <= len(tokens):
        for idx in range(0, len(tokens) - window_size + 1):
            candidates.append(" ".join(tokens[idx : idx + window_size]))

    for token in candidates:
        score = _ratio(norm_query, token)
        if score > best_score:
            best_score = score
            best_token = token

    return FuzzyMatch(
        score=best_score,
        snippet=extract_snippet(text, query, matched_token=best_token),
        exact=False,
        matched_token=best_token,
    )


def extract_snippet(text: str, query: str, matched_token: str = "", span: int = 35) -> str:
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx != -1:
        start = max(idx - span, 0)
        end = min(idx + len(query) + span, len(text))
        return text[start:end]

    if matched_token:
        if " " in matched_token:
            idx = text.lower().find(matched_token.lower())
            if idx != -1:
                start = max(idx - span, 0)
                end = min(idx + len(matched_token) + span, len(text))
                return text[start:end]

        for token_match in re.finditer(r"\S+", text):
            token_raw = token_match.group(0)
            if normalize_text(token_raw) == matched_token:
                start = max(token_match.start() - span, 0)
                end = min(token_match.end() + span, len(text))
                return text[start:end]

    return text[: span * 2]
