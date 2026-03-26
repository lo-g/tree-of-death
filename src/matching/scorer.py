from __future__ import annotations

from src.matching.fuzzy_match import FuzzyMatch


def score_candidate(fuzzy: FuzzyMatch, ocr_confidence: float, index_hint: bool = False) -> float:
    """
    Transparent score formula (0-100):
      final = 0.6*fuzzy_score + 0.3*(ocr_confidence*100) + bonuses - penalties
    Bonuses:
      +8 for exact match
      +6 for index-like page hint
    Penalty:
      -10 if fuzzy score is below 55
    """

    score = 0.6 * fuzzy.score + 0.3 * (ocr_confidence * 100)
    if fuzzy.exact:
        score += 8
    if index_hint:
        score += 6
    if fuzzy.score < 55:
        score -= 10
    return max(0.0, min(100.0, round(score, 2)))
