from __future__ import annotations

import csv

from src.models import SourceProcessingResult
from src.reporting.json_report import as_rows


def write_csv_report(path: str, results: list[SourceProcessingResult]) -> None:
    rows = as_rows(results)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["source", "query", "page_number", "confidence", "snippet", "backend", "origin", "warnings"])
        for row in rows:
            writer.writerow(
                [
                    row.source_id,
                    row.query,
                    row.page_number,
                    row.confidence,
                    row.snippet,
                    row.backend,
                    row.origin,
                    " | ".join(row.warnings),
                ]
            )
