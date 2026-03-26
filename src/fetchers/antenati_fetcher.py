from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from src.cache import CacheStore
from src.models import PageRef

LOGGER = logging.getLogger(__name__)


@dataclass
class FetchPolicy:
    request_delay_seconds: float
    max_pages_remote: int
    max_retries: int


def policy_for_aggressiveness(aggressiveness: str) -> FetchPolicy:
    if aggressiveness == "gentle":
        return FetchPolicy(request_delay_seconds=3.0, max_pages_remote=20, max_retries=1)
    if aggressiveness == "deep":
        return FetchPolicy(request_delay_seconds=1.0, max_pages_remote=200, max_retries=3)
    return FetchPolicy(request_delay_seconds=1.8, max_pages_remote=80, max_retries=2)


class _ImageSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        attrs_dict = dict(attrs)
        src = attrs_dict.get("src")
        if src:
            self.sources.append(src)


class AntenatiFetcher:
    def __init__(self, cache: CacheStore, user_agent: str = "civil-registry-search/0.1 (+respectful)") -> None:
        self.cache = cache
        self.user_agent = user_agent

    def _get(self, url: str, delay_seconds: float, dry_run: bool, max_retries: int) -> tuple[int, bytes | None]:
        if dry_run:
            LOGGER.info("DRY RUN: would request URL %s", url)
            return 0, None

        cache_key = f"http::{url}"
        cached = self.cache.get_binary(cache_key, "bin")
        if cached is not None:
            return 200, cached

        for attempt in range(1, max_retries + 1):
            LOGGER.info("GET %s (attempt %d/%d)", url, attempt, max_retries)
            req = Request(url, headers={"User-Agent": self.user_agent})
            try:
                with urlopen(req, timeout=20) as response:  # noqa: S310
                    status = getattr(response, "status", 200)
                    content = response.read()
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                status = 500
                if "403" in message:
                    status = 403
                elif "429" in message:
                    status = 429
                content = None

            if status in {403, 429}:
                LOGGER.warning("Received status %s from %s. Backing off and stopping.", status, url)
                return status, None
            if status >= 500:
                LOGGER.warning("Server error %s from %s", status, url)
                time.sleep(delay_seconds * 2)
                continue
            if content is not None:
                self.cache.set_binary(cache_key, "bin", content)
            time.sleep(delay_seconds)
            return status, content

        return 500, None

    def discover_pages(self, url: str, policy: FetchPolicy, dry_run: bool, max_pages: int | None = None) -> tuple[list[PageRef], list[str]]:
        warnings: list[str] = []
        status, content = self._get(url, policy.request_delay_seconds, dry_run, policy.max_retries)
        if content is None:
            warnings.append("No response. In dry-run mode no pages are discovered.")
            return [], warnings
        if status in {403, 429}:
            warnings.append("Remote access blocked or rate-limited. Use local-folder mode with manual images.")
            return [], warnings
        if status >= 400:
            warnings.append(f"HTTP error while loading page: {status}")
            return [], warnings

        html = content.decode("utf-8", errors="ignore")
        image_urls = self._extract_image_urls(html, url)
        if not image_urls:
            warnings.append("Could not discover image URLs. Local-folder mode is recommended.")
            return [], warnings

        page_limit = max_pages if max_pages is not None else policy.max_pages_remote
        pages: list[PageRef] = []
        for index, image_url in enumerate(image_urls[:page_limit], start=1):
            pages.append(
                PageRef(
                    source_id=url,
                    page_number=index,
                    page_label=f"page-{index}",
                    image_url=image_url,
                    discovered_from_index=self._looks_like_index_page(image_url),
                )
            )
        return pages, warnings

    def fetch_image_content(self, image_url: str, policy: FetchPolicy, dry_run: bool) -> tuple[bytes | None, list[str]]:
        warnings: list[str] = []
        status, content = self._get(image_url, policy.request_delay_seconds, dry_run, policy.max_retries)
        if content is None:
            warnings.append("No image fetched in dry-run mode.")
            return None, warnings
        if status in {403, 429}:
            warnings.append("Image fetch blocked by server. Use local-folder mode.")
            return None, warnings
        if status >= 400:
            warnings.append(f"Image fetch failed with HTTP {status}")
            return None, warnings
        return content, warnings

    @staticmethod
    def _extract_image_urls(html: str, base_url: str) -> list[str]:
        parser = _ImageSrcParser()
        parser.feed(html)
        urls = []
        for src in parser.sources:
            lower = src.lower()
            if any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".tif", "iiif", "image"]):
                urls.append(urljoin(base_url, src))

        matches = re.findall(r"https?://[^\"']+?(?:jpg|jpeg|png|tif|tiff)", html, re.IGNORECASE)
        urls.extend(matches)

        unique_urls: list[str] = []
        seen: set[str] = set()
        for item in urls:
            if item not in seen:
                seen.add(item)
                unique_urls.append(item)
        return unique_urls

    @staticmethod
    def _looks_like_index_page(marker: str) -> bool:
        marker_l = marker.lower()
        return any(word in marker_l for word in ["indice", "index", "decennale", "annuale"])
