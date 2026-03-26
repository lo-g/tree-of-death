from __future__ import annotations

import argparse
import logging
from pathlib import Path
import re

try:
    from tqdm import tqdm
except Exception:  # noqa: BLE001
    def tqdm(iterable, **_kwargs):
        return iterable

from src.cache import CacheStore
from src.config import ensure_cache_dir, load_config_file, load_query_file, merge_sources, normalize_input
from src.extractors.image_loader import ImageLoader
from src.extractors.page_discovery import PageDiscovery
from src.fetchers.antenati_fetcher import AntenatiFetcher
from src.fetchers.local_folder_fetcher import LocalFolderFetcher
from src.logging_utils import configure_logging
from src.matching.fuzzy_match import match_query
from src.matching.normalize import normalize_text
from src.matching.semantic_reranker import SemanticReranker
from src.matching.scorer import score_candidate
from src.models import MatchResult, SourceDescriptor, SourceProcessingResult
from src.ocr.base import OCRBackend
from src.ocr.factory import SUPPORTED_OCR_BACKENDS, create_ocr_backend
from src.reporting.console_report import build_table_report
from src.reporting.csv_report import write_csv_report
from src.reporting.json_report import build_json_report

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search Italian civil registry pages for names/keywords.")
    parser.add_argument("--url", help="Single remote URL to inspect")
    parser.add_argument("--urls", nargs="*", help="Multiple remote URLs")
    parser.add_argument("--input-folder", help="Local folder with page images")
    parser.add_argument("--query", help="Single query")
    parser.add_argument("--query-file", help="Path to text file with one query per line")
    parser.add_argument("--config", help="JSON config file path")
    parser.add_argument("--aggressiveness", choices=["gentle", "balanced", "deep"], default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--output-format", choices=["table", "json"], default=None)
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ocr-backend", choices=sorted(SUPPORTED_OCR_BACKENDS), default=None)
    parser.add_argument("--ocr-model", default=None)
    parser.add_argument("--semantic-search", action="store_true")
    parser.add_argument("--semantic-threshold", type=float, default=None)
    parser.add_argument("--semantic-model", default=None)
    parser.add_argument("--debug-ocr-text", action="store_true")
    parser.add_argument("--debug-ocr-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser


def _sources_from_input(urls: list[str], input_folder: str | None) -> list[SourceDescriptor]:
    sources = [SourceDescriptor(identifier=url, source_type="remote") for url in urls]
    if input_folder:
        sources.append(SourceDescriptor(identifier=input_folder, source_type="local"))
    return sources


def _origin_for_match(index_flag: bool, exact: bool, semantic_used: bool) -> str:
    if index_flag:
        return "index"
    if exact:
        return "ocr"
    if semantic_used:
        return "semantic"
    return "fuzzy"


def _min_fuzzy_score(query: str) -> float:
    normalized_len = len(normalize_text(query).replace(" ", ""))
    if normalized_len <= 5:
        return 70.0
    if normalized_len <= 8:
        return 65.0
    return 55.0


def _safe_filename_fragment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "unknown"


def run_pipeline(config_payload: dict, ocr_backend: OCRBackend | None = None) -> list[SourceProcessingResult]:
    config = normalize_input(config_payload)

    cache_store = CacheStore(ensure_cache_dir())
    antenati_fetcher = AntenatiFetcher(cache_store)
    local_fetcher = LocalFolderFetcher()
    page_discovery = PageDiscovery(antenati_fetcher=antenati_fetcher, local_fetcher=local_fetcher)
    image_loader = ImageLoader(cache=cache_store, antenati_fetcher=antenati_fetcher)
    backend = ocr_backend or create_ocr_backend(config.ocr_backend, config.ocr_model)
    semantic_reranker = SemanticReranker.from_config(
        enabled=config.semantic_search,
        threshold=config.semantic_threshold,
        model_name=config.semantic_model,
    )
    debug_ocr_dir: Path | None = None
    if config.debug_ocr_text:
        debug_ocr_dir = Path(config.debug_ocr_dir) if config.debug_ocr_dir else ensure_cache_dir() / "ocr_debug"
        debug_ocr_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info("OCR debug enabled. Text dumps will be written to %s", debug_ocr_dir.resolve())

    sources = _sources_from_input(config.urls, config.input_folder)
    results: list[SourceProcessingResult] = []

    for source in sources:
        source_result = SourceProcessingResult(source_id=source.identifier)
        try:
            LOGGER.info("Starting source: %s (%s)", source.identifier, source.source_type)
            pages, discover_warnings = page_discovery.discover(
                source=source,
                aggressiveness=config.aggressiveness,
                dry_run=config.dry_run,
                max_pages=config.max_pages,
            )
            source_result.warnings.extend(discover_warnings)
            LOGGER.info("Discovered %d page(s) for source: %s", len(pages), source.identifier)
            if not pages:
                source_result.warnings.append("No pages discovered for this source.")
                results.append(source_result)
                continue

            total_pages = len(pages)
            for page_index, page in enumerate(tqdm(pages, desc=f"Processing {source.identifier}", unit="page"), start=1):
                if total_pages <= 50 or page_index == 1 or page_index == total_pages or page_index % 10 == 0:
                    LOGGER.info("Processing page %d/%d: %s", page_index, total_pages, page.page_label)
                image, image_warnings = image_loader.load_page_image(
                    page,
                    aggressiveness=config.aggressiveness,
                    dry_run=config.dry_run,
                )
                source_result.warnings.extend(image_warnings)
                if image is None:
                    continue

                ocr_result = backend.extract_text(image)
                if config.debug_ocr_text:
                    preview = re.sub(r"\s+", " ", ocr_result.text).strip()
                    preview = preview[:220] if preview else "<empty>"
                    LOGGER.info(
                        "OCR READ source=%s page=%s backend=%s conf=%.2f chars=%d preview=%s",
                        source.identifier,
                        page.page_label,
                        ocr_result.backend,
                        ocr_result.confidence,
                        len(ocr_result.text),
                        preview,
                    )
                    if not ocr_result.text.strip():
                        LOGGER.warning(
                            "OCR EMPTY source=%s page=%s backend=%s",
                            source.identifier,
                            page.page_label,
                            ocr_result.backend,
                        )
                    if debug_ocr_dir is not None:
                        dump_name = (
                            f"{_safe_filename_fragment(source.identifier)}__"
                            f"p{page.page_number:04d}__"
                            f"{_safe_filename_fragment(page.page_label)}.txt"
                        )
                        dump_path = debug_ocr_dir / dump_name
                        dump_path.write_text(ocr_result.text, encoding="utf-8", errors="ignore")

                for query in config.queries:
                    fuzzy = match_query(ocr_result.text, query)
                    if fuzzy.score < _min_fuzzy_score(query):
                        continue

                    semantic_score = None
                    semantic_used = False
                    if semantic_reranker.is_ready and not fuzzy.exact:
                        semantic_score = semantic_reranker.score(query=query, text=ocr_result.text)
                        semantic_used = semantic_score is not None
                        if not semantic_reranker.passes_threshold(semantic_score):
                            continue

                    confidence = score_candidate(
                        fuzzy=fuzzy,
                        ocr_confidence=ocr_result.confidence,
                        index_hint=page.discovered_from_index,
                    )
                    if semantic_score is not None:
                        confidence = round(min(100.0, 0.75 * confidence + 0.25 * semantic_score), 2)

                    source_result.matches.append(
                        MatchResult(
                            source_id=source.identifier,
                            query=query,
                            page_number=page.page_number,
                            confidence=confidence,
                            snippet=fuzzy.snippet,
                            backend=ocr_result.backend,
                            origin=_origin_for_match(page.discovered_from_index, fuzzy.exact, semantic_used),
                            semantic_score=semantic_score,
                            warnings=list(image_warnings),
                        )
                    )

            source_result.matches.sort(key=lambda item: item.confidence, reverse=True)
            LOGGER.info(
                "Completed source: %s | matches=%d warnings=%d errors=%d",
                source.identifier,
                len(source_result.matches),
                len(source_result.warnings),
                len(source_result.errors),
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed to process source %s", source.identifier)
            source_result.errors.append(str(exc))

        results.append(source_result)

    return results


def run_cli() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    cli_payload = {
        "url": args.url,
        "urls": args.urls,
        "input_folder": args.input_folder,
        "query": args.query,
        "aggressiveness": args.aggressiveness,
        "max_pages": args.max_pages,
        "output_format": args.output_format,
        "csv_output": args.csv_output,
        "dry_run": args.dry_run,
        "ocr_backend": args.ocr_backend,
        "ocr_model": args.ocr_model,
        "semantic_search": args.semantic_search,
        "semantic_threshold": args.semantic_threshold,
        "semantic_model": args.semantic_model,
        "debug_ocr_text": args.debug_ocr_text,
        "debug_ocr_dir": args.debug_ocr_dir,
    }

    queries_from_file = load_query_file(args.query_file) if args.query_file else []
    if queries_from_file:
        cli_payload["queries"] = queries_from_file

    file_payload = load_config_file(args.config) if args.config else None
    merged = merge_sources(cli_payload=cli_payload, file_payload=file_payload)

    results = run_pipeline(merged)

    output_format = merged.get("output_format", "table")
    if output_format == "json":
        print(build_json_report(results))
    else:
        print(build_table_report(results))

    if merged.get("csv_output"):
        write_csv_report(merged["csv_output"], results)
        LOGGER.info("CSV report written to %s", Path(merged["csv_output"]).resolve())
