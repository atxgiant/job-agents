from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import load_runtime_config


class CandidateProfileUnavailableError(FileNotFoundError):
    """Raised when a required private candidate profile is unavailable."""


@dataclass(slots=True)
class CandidateProfile:
    source_path: Path
    content_hash: str
    loaded_at: datetime
    raw_text: str


class CandidateProfileService:
    def __init__(self, source_path: str | None = None) -> None:
        config = load_runtime_config()
        self.source_path = Path(source_path or config.candidate_profile_path)

    def _resolve_source_path(self) -> Path:
        if self.source_path.exists():
            return self.source_path

        raise CandidateProfileUnavailableError(
            f"Private candidate profile file not found at {self.source_path}"
        )

    def load_required(self) -> CandidateProfile:
        source_path = self._resolve_source_path()
        raw_text = source_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        return CandidateProfile(
            source_path=source_path,
            content_hash=content_hash,
            loaded_at=datetime.now(UTC),
            raw_text=raw_text,
        )

    def load_optional(self) -> CandidateProfile | None:
        try:
            return self.load_required()
        except CandidateProfileUnavailableError:
            return None

    def load(self) -> CandidateProfile:
        return self.load_required()
