from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.models import OCRResult


class OCRBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def extract_text(self, image: Any) -> OCRResult:
        raise NotImplementedError
