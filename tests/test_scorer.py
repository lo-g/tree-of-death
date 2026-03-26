from src.matching.fuzzy_match import FuzzyMatch
from src.matching.scorer import score_candidate


def test_score_candidate_applies_bonuses() -> None:
    fuzzy = FuzzyMatch(score=92, snippet="", exact=True)
    score = score_candidate(fuzzy, ocr_confidence=0.7, index_hint=True)
    assert score > 90
