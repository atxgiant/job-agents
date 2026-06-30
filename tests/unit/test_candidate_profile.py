from app.services.candidate_profile import CandidateProfileService


def test_candidate_profile_loads_configured_or_fallback_file():
    profile = CandidateProfileService("skillset.local.md").load()
    assert profile.content_hash
    assert "Skillset" in profile.raw_text or "Canonical" in profile.raw_text
