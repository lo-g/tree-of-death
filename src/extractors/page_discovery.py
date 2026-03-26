from __future__ import annotations

from src.fetchers.antenati_fetcher import AntenatiFetcher, policy_for_aggressiveness
from src.fetchers.local_folder_fetcher import LocalFolderFetcher
from src.models import PageRef, SourceDescriptor


class PageDiscovery:
    def __init__(self, antenati_fetcher: AntenatiFetcher, local_fetcher: LocalFolderFetcher) -> None:
        self.antenati_fetcher = antenati_fetcher
        self.local_fetcher = local_fetcher

    def discover(
        self,
        source: SourceDescriptor,
        aggressiveness: str,
        dry_run: bool,
        max_pages: int | None,
    ) -> tuple[list[PageRef], list[str]]:
        if source.source_type == "local":
            pages = self.local_fetcher.discover_pages(source.identifier, max_pages=max_pages)
            return pages, []

        policy = policy_for_aggressiveness(aggressiveness)
        return self.antenati_fetcher.discover_pages(
            source.identifier,
            policy=policy,
            dry_run=dry_run,
            max_pages=max_pages,
        )
