from __future__ import annotations

from pathlib import Path
from typing import Any

from src.models import OCRResult
from src.ocr.base import OCRBackend


class SimpleOCRBackend(OCRBackend):
    """Simple placeholder backend based on optional sidecar text files."""

    @property
    def name(self) -> str:
        return "simple-sidecar"

    def extract_text(self, image: Any) -> OCRResult:
        image_filename = getattr(image, "filename", "")
        if image_filename:
            sidecar = Path(image_filename).with_suffix(".txt")
            if sidecar.exists():
                text = sidecar.read_text(encoding="utf-8", errors="ignore")
                return OCRResult(text=text, confidence=0.8, backend=self.name)

        return OCRResult(text="", confidence=0.05, backend=self.name)
