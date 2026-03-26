from __future__ import annotations

from src.models import SourceProcessingResult
from src.reporting.json_report import as_rows


def build_table_report(results: list[SourceProcessingResult]) -> str:
    rows = as_rows(results)
    if not rows:
        return "No matches found."

    headers = ["Source", "Query", "Page", "Confidence", "Backend", "Origin", "Snippet"]
    data = [
        [
            row.source_id,
            row.query,
            str(row.page_number),
            f"{row.confidence:.2f}",
            row.backend,
            row.origin,
            row.snippet.replace("\n", " ")[:70],
        ]
        for row in rows
    ]

    col_widths = [len(header) for header in headers]
    for line in data:
        for idx, cell in enumerate(line):
            col_widths[idx] = max(col_widths[idx], len(cell))

    def format_row(values: list[str]) -> str:
        return " | ".join(value.ljust(col_widths[idx]) for idx, value in enumerate(values))

    separator = "-+-".join("-" * width for width in col_widths)
    lines = [format_row(headers), separator]
    lines.extend(format_row(line) for line in data)
    return "\n".join(lines)
