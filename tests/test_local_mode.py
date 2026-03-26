from pathlib import Path

from src.cli import run_pipeline
from src.models import OCRResult
from src.ocr.base import OCRBackend


class MockOCRBackend(OCRBackend):
    @property
    def name(self) -> str:
        return "mock"

    def extract_text(self, image) -> OCRResult:
        filename = Path(getattr(image, "filename", "")).name
        if filename.startswith("0001"):
            return OCRResult(text="Registro: Giovanni Bourne", confidence=0.9, backend=self.name)
        return OCRResult(text="Nessuna corrispondenza", confidence=0.8, backend=self.name)


def test_local_folder_mode_finds_candidate(tmp_path: Path) -> None:
    image_path = tmp_path / "0001.jpg"
    image_path.write_bytes(b"fake-image")

    payload = {
        "input_folder": str(tmp_path),
        "queries": ["Giovanni"],
        "output_format": "json",
    }
    results = run_pipeline(payload, ocr_backend=MockOCRBackend())

    assert len(results) == 1
    assert results[0].matches
    assert results[0].matches[0].page_number == 1
    assert results[0].matches[0].confidence >= 80
