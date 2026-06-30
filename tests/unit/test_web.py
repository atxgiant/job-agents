from app.web.app import create_app


def test_healthcheck_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_dashboard_renders_when_private_profile_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.services.candidate_profile.CandidateProfileService.load_optional",
        lambda self: None,
    )
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert (
        b"Candidate profile unavailable" in response.data or b"Candidate Profile" in response.data
    )
