from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.models import SearchInput

_ALLOWED_AGGRESSIVENESS = {"gentle", "balanced", "deep"}
_ALLOWED_OUTPUT = {"table", "json"}


def load_config_file(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def merge_sources(cli_payload: dict[str, Any], file_payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(file_payload or {})
    for key, value in cli_payload.items():
        if value is not None:
            merged[key] = value
    return merged


def load_query_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def normalize_input(payload: dict[str, Any]) -> SearchInput:
    urls = payload.get("urls") or []
    single_url = payload.get("url")
    if single_url:
        urls = [single_url] + [u for u in urls if u != single_url]

    queries = payload.get("queries") or []
    single_query = payload.get("query")
    if single_query:
        queries = [single_query] + [q for q in queries if q != single_query]

    aggressiveness = payload.get("aggressiveness", "balanced")
    if aggressiveness not in _ALLOWED_AGGRESSIVENESS:
        raise ValueError(f"Invalid aggressiveness: {aggressiveness}")

    output_format = payload.get("output_format", "table")
    if output_format not in _ALLOWED_OUTPUT:
        raise ValueError(f"Invalid output format: {output_format}")

    result = SearchInput(
        urls=urls,
        input_folder=payload.get("input_folder"),
        queries=queries,
        aggressiveness=aggressiveness,
        max_pages=payload.get("max_pages"),
        output_format=output_format,
        csv_output=payload.get("csv_output"),
        dry_run=bool(payload.get("dry_run", False)),
    )

    if not result.urls and not result.input_folder:
        raise ValueError("At least one URL or --input-folder is required")
    if not result.queries:
        raise ValueError("At least one query is required")

    return result


def to_dict(config: SearchInput) -> dict[str, Any]:
    return asdict(config)


def ensure_cache_dir() -> Path:
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)
    return cache_dir
