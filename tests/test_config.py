from src.config import normalize_input


def test_config_parsing_supports_single_url_and_query() -> None:
    config = normalize_input({"url": "https://example.test", "query": "Giovanni"})
    assert config.urls == ["https://example.test"]
    assert config.queries == ["Giovanni"]


def test_config_requires_source() -> None:
    try:
        normalize_input({"query": "x"})
    except ValueError as exc:
        assert "URL or --input-folder" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
