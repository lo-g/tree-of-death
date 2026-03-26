from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class CacheStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str, suffix: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.base_dir / f"{digest}.{suffix}"

    def get_json(self, key: str) -> dict[str, Any] | None:
        path = self._path_for_key(key, "json")
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def set_json(self, key: str, payload: dict[str, Any]) -> None:
        path = self._path_for_key(key, "json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def get_binary(self, key: str, suffix: str) -> bytes | None:
        path = self._path_for_key(key, suffix)
        if not path.exists():
            return None
        return path.read_bytes()

    def set_binary(self, key: str, suffix: str, content: bytes) -> Path:
        path = self._path_for_key(key, suffix)
        path.write_bytes(content)
        return path
