from __future__ import annotations

import asyncio

import httpx

from app.models.company import Company
from app.models.enums import CompanyStatus, CompanyType
from app.scanners.ats.greenhouse import GreenhouseAdapter, SourceScanError


class FakeAsyncClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error

    async def get(self, _url: str):
        if self.error:
            raise self.error
        return self.response

    async def aclose(self):
        return None


def make_company(**overrides):
    payload = {
        "id": 1,
        "name": "Acme Robotics",
        "normalized_name": "acme robotics",
        "company_type": CompanyType.PUBLIC,
        "status": CompanyStatus.ACTIVE,
        "ats_provider": "greenhouse",
        "ats_company_identifier": "acme",
    }
    payload.update(overrides)
    return Company(**payload)


def test_validate_company_source_accepts_board_token():
    adapter = GreenhouseAdapter()
    result = asyncio.run(adapter.validate_company_source(make_company()))

    assert result.valid is True
    assert result.authoritative is True
    assert result.board_token == "acme"


def test_discover_jobs_parses_greenhouse_board():
    response = httpx.Response(
        200,
        json={
            "jobs": [
                {
                    "id": 123,
                    "title": "Senior Program Manager",
                    "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/123",
                    "location": {"name": "Austin, TX"},
                    "metadata": [{"name": "Department", "value": "Operations"}],
                    "content": "<div><p>Hello <strong>world</strong>.</p></div>",
                    "updated_at": "2026-06-29T12:00:00Z",
                }
            ]
        },
    )
    adapter = GreenhouseAdapter(client=FakeAsyncClient(response=response))

    jobs = asyncio.run(adapter.discover_jobs(make_company()))

    assert len(jobs) == 1
    assert jobs[0].external_job_id == "123"
    assert jobs[0].description_text == "Hello world."
    assert jobs[0].source_url == "https://job-boards.greenhouse.io/acme/jobs/123"


def test_discover_jobs_handles_empty_board():
    response = httpx.Response(200, json={"jobs": []})
    adapter = GreenhouseAdapter(client=FakeAsyncClient(response=response))

    jobs = asyncio.run(adapter.discover_jobs(make_company()))

    assert jobs == []


def test_discover_jobs_raises_for_malformed_response():
    response = httpx.Response(200, json={"unexpected": []})
    adapter = GreenhouseAdapter(client=FakeAsyncClient(response=response))

    try:
        asyncio.run(adapter.discover_jobs(make_company()))
    except SourceScanError as exc:
        assert exc.error_code == "source_incomplete"
    else:
        raise AssertionError("Expected SourceScanError")


def test_discover_jobs_raises_for_timeout():
    adapter = GreenhouseAdapter(client=FakeAsyncClient(error=httpx.TimeoutException("timeout")))

    try:
        asyncio.run(adapter.discover_jobs(make_company()))
    except SourceScanError as exc:
        assert exc.error_code == "source_timeout"
    else:
        raise AssertionError("Expected SourceScanError")


def test_validate_company_source_requires_configuration():
    adapter = GreenhouseAdapter()
    result = asyncio.run(
        adapter.validate_company_source(
            make_company(ats_company_identifier=None, careers_url="https://example.com/careers")
        )
    )

    assert result.valid is False
    assert result.error_code == "missing_ats_configuration"
