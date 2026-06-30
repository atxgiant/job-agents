# Head Hunter

Head Hunter is a local-first personal job-search agent for discovering, classifying, ranking, and tracking roles from official company career sources. It is designed to run entirely on a developer workstation with SQLite, Flask, and locally hosted Temporal.

## Current status

The repository now includes the Phase 2 company-registry vertical slice:

- Flask app factory and Bootstrap dashboard shell
- Typed settings loading from YAML and `.env`
- Candidate profile loading from a private local markdown file with fail-closed behavior for candidate-specific workflows
- SQLAlchemy models and Alembic migration scaffold
- Local Temporal Docker Compose stack
- Company lifecycle services and persistent audit events
- Company registry UI with create, edit, activate, deactivate, reject, exclude, reactivate, and scan-block assignment actions
- CSV import and export with validation reporting and idempotent upsert logic
- Deterministic scan-block rebalance preview and apply flow
- CLI and Makefile entrypoints
- Initial docs and baseline tests

## Private candidate profile workflow

This repo includes a public [SKILLSET.md](./SKILLSET.md) template and expects your real private profile to live in `skillset.local.md` or another local path configured in `config/settings.example.yaml`.

Private candidate profile files are gitignored so you can store role history, quantified achievements, targeting logic, and other personal material without committing it. `skillset.md` is not an active convention in this project.

If `skillset.local.md` is unavailable, the UI still renders, but candidate-specific workflows must fail closed instead of generating empty ranking or reseeding output.

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

- ATS scanning, job lifecycle management, LLM-assisted reseeding, and job scoring are not implemented yet.
- Temporal workflows and worker activities remain in a pre-production scaffold stage.
