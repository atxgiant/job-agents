# Head Hunter Context

Head Hunter is a local-first personal job-search application for maintaining a target-company registry, discovering official-source job opportunities, tracking review outcomes, and orchestrating recurring local workflows with Temporal. The system is deliberately modular so later daVinci integrations can consume structured company, job, and candidate-profile data without coupling themselves to Flask routes or direct database access.

## Candidate profile convention

- `SKILLSET.md`: public repository template only
- `skillset.local.md`: private local candidate profile only
- Default configured candidate profile path: `skillset.local.md`
- `skillset.local.md` must be gitignored
- Candidate-specific workflows must fail closed when the private profile is unavailable

The UI may render in a profile-unavailable state, but any future candidate-specific workflow such as reseeding, ranking, scoring, or digest generation must stop with a clear local error rather than generating empty or misleading output.

## Company lifecycle states

- `active`
- `inactive`
- `rejected`
- `excluded`

## Job review statuses for later phases

- `not_reviewed`
- `rejected`
- `interested`
- `applied`

## Career-site statuses for later phases

- `active`
- `removed`
- `unknown`
- `scan_failed`
- `unsupported`

## Required invariants

1. A rejected company must never be silently re-added or reactivated by reseeding.
2. Canonical must be configurable as an excluded company, not hard-coded into business logic.
3. Job discovery may use only official company career pages and official company-operated ATS pages.
4. Company reseeding may use broader LLM-assisted research, but that permission never extends to job discovery.
5. Qualifying reseeded companies should be automatically activated unless excluded or previously rejected.
6. The active registry is divided into rotating scan blocks; the initial default is one block per daily run.
7. The initial digest default is weekly, but schedule and frequency are configuration-driven.
8. SQLite is the authoritative persistent business-state store.
9. Temporal is the durable workflow orchestration and execution-history layer, not the business system of record.
10. All future workflows must preserve manual user decisions and never overwrite company rejection, job review status, notes, or applied dates.

## Job lifecycle rules

- Every newly discovered posting starts as `review_status = not_reviewed`.
- Every newly discovered posting starts as `career_site_status = active` unless the source is incomplete or ambiguous.
- `first_seen_at` is immutable once set.
- `last_seen_at` updates when the role appears in a successful authoritative scan.
- `last_verified_at` updates when the role is checked.
- A successful authoritative scan may mark previously active jobs as `removed` when they disappear from the official source.
- Failed, incomplete, or unsupported scans must never mark jobs as removed.
- If a removed job reappears in a later authoritative scan, it returns to `active` without losing its history.
- Manual review status, notes, rejection reason, and applied date are immutable to scans.

## Job source-of-truth rules

- SQLite remains the authoritative job state store.
- Official Greenhouse source responses are authoritative only when the scan completes successfully and the board response is complete.
- Job scan observations preserve what the source looked like during a specific scan.
- Job status history preserves manual and system state transitions separately from the current row snapshot.

## Initial target-company policy example

This policy must remain configurable data rather than application logic:

- Seed from Russell 1000 public companies and pre-IPO look-alike companies.
- Prefer physical products, connected products, field-deployed technology, and technology-enabled physical services.
- Prioritize consumer and retail, EV and mobility, industrial technology, smart home and building systems, logistics, robotics, and autonomous systems.
- Avoid pure-play horizontal SaaS absent a substantial hardware, device, deployment, or physical-world component.
- Exclude oil and gas, pharma, insurance, healthcare, and Canonical.
- Automatically activate qualifying companies unless the user has rejected or excluded them.

## Current scope

- Local Flask UI
- SQLite system of record
- Local Temporal orchestration
- Company registry lifecycle management
- CSV import and export for company portability
- Candidate profile loading with fail-closed behavior for candidate-specific operations

## Non-goals in the current phase

- ATS scanning
- LLM-assisted reseeding
- Job scoring
- Weekly digest generation
- Resume generation
- daVinci implementation
- Google Drive or Google Docs integration
- Cloud-managed scheduler, queue, or database

## Extension boundary

Future daVinci integration should consume structured candidate-profile context, selected job records, company context, and fit-analysis results through service boundaries rather than Flask templates or direct ORM calls.
