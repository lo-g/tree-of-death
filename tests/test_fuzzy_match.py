from src.matching.fuzzy_match import match_query


def test_fuzzy_match_exact() -> None:
    result = match_query("Atto di nascita: Giovanni Rossi", "Giovanni")
    assert result.exact is True
    assert result.score == 100.0


def test_fuzzy_match_partial() -> None:
    result = match_query("Sebastiano Montanari", "Sebastiano Montanaro")
    assert result.score > 70
