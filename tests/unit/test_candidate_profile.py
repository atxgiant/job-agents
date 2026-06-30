from pathlib import Path

import pytest

from app.services.candidate_profile import (
    CandidateProfileService,
    CandidateProfileUnavailableError,
)


def test_candidate_profile_loads_private_local_file():
    profile = CandidateProfileService("skillset.local.md").load_required()
    assert profile.content_hash
    assert "Canonical" in profile.raw_text


def test_candidate_profile_optional_load_returns_none_when_missing(tmp_path: Path):
    profile = CandidateProfileService(str(tmp_path / "missing.local.md")).load_optional()
    assert profile is None


def test_candidate_profile_required_load_fails_closed_when_missing(tmp_path: Path):
    with pytest.raises(CandidateProfileUnavailableError):
        CandidateProfileService(str(tmp_path / "missing.local.md")).load_required()
