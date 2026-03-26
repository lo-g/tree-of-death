from __future__ import annotations

import argparse
import logging
from pathlib import Path

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
from src.matching.scorer import score_candidate
from src.models import MatchResult, SourceDescriptor, SourceProcessingResult
from src.ocr.base import OCRBackend
from src.ocr.simple_backend import SimpleOCRBackend
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
    parser.add_argument("--verbose", action="store_true")
    return parser


def _sources_from_input(urls: list[str], input_folder: str | None) -> list[SourceDescriptor]:
    sources = [SourceDescriptor(identifier=url, source_type="remote") for url in urls]
    if input_folder:
        sources.append(SourceDescriptor(identifier=input_folder, source_type="local"))
    return sources


def _origin_for_match(index_flag: bool, exact: bool) -> str:
    if index_flag:
        return "index"
    if exact:
        return "ocr"
    return "fuzzy"


def run_pipeline(config_payload: dict, ocr_backend: OCRBackend | None = None) -> list[SourceProcessingResult]:
    config = normalize_input(config_payload)

    cache_store = CacheStore(ensure_cache_dir())
    antenati_fetcher = AntenatiFetcher(cache_store)
    local_fetcher = LocalFolderFetcher()
    page_discovery = PageDiscovery(antenati_fetcher=antenati_fetcher, local_fetcher=local_fetcher)
    image_loader = ImageLoader(cache=cache_store, antenati_fetcher=antenati_fetcher)
    backend = ocr_backend or SimpleOCRBackend()

    sources = _sources_from_input(config.urls, config.input_folder)
    results: list[SourceProcessingResult] = []

    for source in sources:
        source_result = SourceProcessingResult(source_id=source.identifier)
        try:
            pages, discover_warnings = page_discovery.discover(
                source=source,
                aggressiveness=config.aggressiveness,
                dry_run=config.dry_run,
                max_pages=config.max_pages,
            )
            source_result.warnings.extend(discover_warnings)
            if not pages:
                source_result.warnings.append("No pages discovered for this source.")
                results.append(source_result)
                continue

            for page in tqdm(pages, desc=f"Processing {source.identifier}", unit="page"):
                image, image_warnings = image_loader.load_page_image(
                    page,
                    aggressiveness=config.aggressiveness,
                    dry_run=config.dry_run,
                )
                source_result.warnings.extend(image_warnings)
                if image is None:
                    continue

                ocr_result = backend.extract_text(image)
                for query in config.queries:
                    fuzzy = match_query(ocr_result.text, query)
                    if fuzzy.score < 45:
                        continue

                    confidence = score_candidate(
                        fuzzy=fuzzy,
                        ocr_confidence=ocr_result.confidence,
                        index_hint=page.discovered_from_index,
                    )

                    source_result.matches.append(
                        MatchResult(
                            source_id=source.identifier,
                            query=query,
                            page_number=page.page_number,
                            confidence=confidence,
                            snippet=fuzzy.snippet,
                            backend=ocr_result.backend,
                            origin=_origin_for_match(page.discovered_from_index, fuzzy.exact),
                            warnings=list(image_warnings),
                        )
                    )

            source_result.matches.sort(key=lambda item: item.confidence, reverse=True)
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
