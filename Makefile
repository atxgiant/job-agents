PYTHON ?= python3

.PHONY: setup test lint format db-upgrade temporal-up temporal-down worker web seed scan digest

setup:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .
	mypy app

format:
	ruff format .

db-upgrade:
	alembic upgrade head

temporal-up:
	docker compose up -d temporal temporal-ui

temporal-down:
	docker compose down

worker:
	head-hunter worker

web:
	head-hunter serve

seed:
	head-hunter reseed

scan:
	head-hunter scan all

digest:
	head-hunter digest weekly
