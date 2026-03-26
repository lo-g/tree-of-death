from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.cache import CacheStore
from src.fetchers.antenati_fetcher import AntenatiFetcher, policy_for_aggressiveness
from src.models import PageRef


@dataclass
class LoadedImage:
    filename: str
    content: bytes


class ImageLoader:
    def __init__(self, cache: CacheStore, antenati_fetcher: AntenatiFetcher) -> None:
        self.cache = cache
        self.antenati_fetcher = antenati_fetcher

    def load_page_image(self, page: PageRef, aggressiveness: str, dry_run: bool) -> tuple[LoadedImage | None, list[str]]:
        if page.local_path:
            content = page.local_path.read_bytes()
            return LoadedImage(filename=str(page.local_path), content=content), []

        if not page.image_url:
            return None, ["No image URL available for page."]

        policy = policy_for_aggressiveness(aggressiveness)
        content, warnings = self.antenati_fetcher.fetch_image_content(page.image_url, policy, dry_run=dry_run)
        if content is None:
            return None, warnings

        cache_key = f"img::{page.image_url}"
        self.cache.set_binary(cache_key, "img", content)
        return LoadedImage(filename=page.image_url, content=content), warnings

    @staticmethod
    def export_image(content: bytes, path: Path) -> None:
        path.write_bytes(content)
