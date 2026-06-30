# Head Hunter

Head Hunter is a local-first personal job-search agent for discovering, classifying, ranking, and tracking roles from official company career sources. It is designed to run entirely on a developer workstation with SQLite, Flask, and locally hosted Temporal.

## Current status

The repository now includes the Phase 3 Greenhouse job-ingestion vertical slice:

- Flask app factory and Bootstrap dashboard shell
- Typed settings loading from YAML and `.env`
- Candidate profile loading from a private local markdown file with fail-closed behavior for candidate-specific workflows
- SQLAlchemy models and Alembic migration scaffold
- Local Temporal Docker Compose stack
- Company lifecycle services and persistent audit events
- Company registry UI with create, edit, activate, deactivate, reject, exclude, reactivate, and scan-block assignment actions
- CSV import and export with validation reporting and idempotent upsert logic
- Deterministic scan-block rebalance preview and apply flow
- Greenhouse-only official-source job ingestion for a manually scanned company
- Job lifecycle persistence with observations, status history, and removal detection
- Opportunities review UI with manual review statuses, notes, and CSV export
- CLI and Makefile entrypoints
- Initial docs and baseline tests

## Private candidate profile workflow

This repo includes a public [SKILLSET.md](./SKILLSET.md) template and expects your real private profile to live in `skillset.local.md` or another local path configured in `config/settings.example.yaml`.

Private candidate profile files are gitignored so you can store role history, quantified achievements, targeting logic, and other personal material without committing it. `skillset.md` is not an active convention in this project.

If `skillset.local.md` is unavailable, the UI still renders, but candidate-specific workflows must fail closed instead of generating empty ranking or reseeding output.

## Configure a Greenhouse company

Set the company to:

- `status = active`
- `ats_provider = greenhouse`
- `ats_company_identifier = <greenhouse board token>`

You can also provide an official Greenhouse board URL through the company configuration, but the board token is the cleanest setup.

## Run a manual Greenhouse scan

1. Open the Companies page.
2. Create or edit an active company with Greenhouse configuration.
3. Open the company detail page.
4. Use `Scan Greenhouse Board`.

The scan creates a scan run, fetches roles from the official Greenhouse source, normalizes and ingests the results, and updates discovered jobs on both the company detail page and the Opportunities view.

## Review status vs career-site status

- Review status is the local user decision: `not_reviewed`, `interested`, `rejected`, or `applied`.
- Career-site status is the source-derived availability state: `active`, `removed`, `unknown`, `scan_failed`, or `unsupported`.

Scans may change career-site status, but they must not overwrite manual review decisions, notes, rejection reasons, or applied dates.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make setup
cp .env.example .env
alembic upgrade head
docker compose up -d temporal temporal-ui
head-hunter serve
```

## Common commands

```bash
make test
make lint
ruff format --check .
make db-upgrade
make temporal-up
make temporal-down
make web
make worker
```

## Local services

- Web app: `http://127.0.0.1:5000`
- Temporal gRPC: `localhost:7233`
- Temporal UI: `http://127.0.0.1:8233`

## Privacy and repository safety

- Do not commit `.env`, API keys, browser cookies, or local database files.
- Do not commit private candidate profile content.
- Use the public `SKILLSET.md` template for repository examples.

## Known limitations

- Greenhouse is the only supported ATS provider in this phase.
- Manual single-company scans are supported; scheduled and batch scans are not yet behind Temporal activities.
- LLM scoring, multi-provider ATS support, reseeding, and daVinci workflows are not implemented yet.
