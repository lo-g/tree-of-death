from __future__ import annotations

from pathlib import Path

from src.models import PageRef

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


class LocalFolderFetcher:
    def discover_pages(self, folder: str, max_pages: int | None = None) -> list[PageRef]:
        root = Path(folder)
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Input folder not found: {folder}")

        image_files = sorted(
            [file for file in root.iterdir() if file.is_file() and file.suffix.lower() in _IMAGE_EXTENSIONS]
        )
        if max_pages is not None:
            image_files = image_files[:max_pages]

        pages: list[PageRef] = []
        for index, image_file in enumerate(image_files, start=1):
            pages.append(
                PageRef(
                    source_id=str(root),
                    page_number=index,
                    page_label=image_file.name,
                    local_path=image_file,
                )
            )
        return pages
