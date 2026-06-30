# ATS Adapters

Phase 3 implements one official-source adapter: Greenhouse.

## Contract

Adapters should expose:

- provider identification
- company source validation
- job discovery from the official source
- raw provider metadata that can be normalized before persistence

Conceptually:

```python
class JobSourceAdapter(Protocol):
    provider_name: str

    def can_handle(self, company): ...
    async def validate_company_source(self, company): ...
    async def discover_jobs(self, company): ...
```

## Greenhouse requirements

Head Hunter expects:

- `ats_provider = greenhouse`
- `ats_company_identifier` set to the Greenhouse board token, or
- an official Greenhouse board URL discoverable from company configuration

Only official Greenhouse board pages or official Greenhouse board API responses are valid inputs.

## Testing strategy

- fixture-backed valid board response
- empty board response
- malformed response
- timeout and HTTP error handling
- HTML-to-text normalization
- stable external job ID extraction

## Rules for future adapters

- official-source only
- no generic job board aggregation
- no CAPTCHA or auth bypass
- no removal detection from incomplete or failed scans
- raw provider parsing separated from normalized application records
