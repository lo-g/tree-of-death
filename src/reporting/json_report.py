from __future__ import annotations

import json
from dataclasses import asdict

from src.models import MatchResult, SourceProcessingResult


def build_json_report(results: list[SourceProcessingResult]) -> str:
    payload = []
    for item in results:
        payload.append(
            {
                "source": item.source_id,
                "warnings": item.warnings,
                "errors": item.errors,
                "matches": [asdict(match) for match in item.matches],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def as_rows(results: list[SourceProcessingResult]) -> list[MatchResult]:
    rows: list[MatchResult] = []
    for source in results:
        rows.extend(source.matches)
    return rows
