from src.matching.normalize import normalize_text


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("Giovánni, D'Ángelo!") == "giovanni d angelo"
