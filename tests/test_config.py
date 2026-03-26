from src.config import normalize_input


def test_config_parsing_supports_single_url_and_query() -> None:
    config = normalize_input({"url": "https://example.test", "query": "Giovanni"})
    assert config.urls == ["https://example.test"]
    assert config.queries == ["Giovanni"]


def test_config_defaults_to_local_input_folder_when_source_missing() -> None:
    config = normalize_input({"query": "x"})
    assert config.input_folder is not None


def test_config_parses_ocr_backend_options() -> None:
    config = normalize_input({"query": "x", "ocr_backend": "trocr", "ocr_model": "microsoft/trocr-large-handwritten"})
    assert config.ocr_backend == "trocr"
    assert config.ocr_model == "microsoft/trocr-large-handwritten"
