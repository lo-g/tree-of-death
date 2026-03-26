from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Aggressiveness = Literal["gentle", "balanced", "deep"]
SourceType = Literal["remote", "local"]
MatchOrigin = Literal["index", "ocr", "fuzzy", "semantic"]


@dataclass
class SearchInput:
    urls: list[str] = field(default_factory=list)
    input_folder: str | None = None
    queries: list[str] = field(default_factory=list)
    aggressiveness: Aggressiveness = "balanced"
    max_pages: int | None = None
    output_format: Literal["table", "json"] = "table"
    csv_output: str | None = None
    dry_run: bool = False
    semantic_search: bool = False
    semantic_threshold: float = 42.0
    semantic_model: str | None = None
    debug_ocr_text: bool = False
    debug_ocr_dir: str | None = None
    ocr_backend: str = "hybrid"
    ocr_model: str | None = None


@dataclass
class SourceDescriptor:
    identifier: str
    source_type: SourceType


@dataclass
class PageRef:
    source_id: str
    page_number: int
    page_label: str
    image_url: str | None = None
    local_path: Path | None = None
    discovered_from_index: bool = False


@dataclass
class OCRResult:
    text: str
    confidence: float
    backend: str


@dataclass
class MatchResult:
    source_id: str
    query: str
    page_number: int
    confidence: float
    snippet: str
    backend: str
    origin: MatchOrigin
    semantic_score: float | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class SourceProcessingResult:
    source_id: str
    matches: list[MatchResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
