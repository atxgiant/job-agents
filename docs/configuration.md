# Configuration

Head Hunter uses YAML plus environment variables.

## Files

- `config/settings.example.yaml`
- `config/seed-policy.example.yaml`
- `config/scan-policy.example.yaml`
- `.env.example`
- `SKILLSET.md` public template
- `skillset.local.md` private candidate profile

## Environment variables

- `DATABASE_URL`
- `TEMPORAL_ADDRESS`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TASK_QUEUE`
- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OPENAI_MONTHLY_BUDGET_USD`
- `FLASK_SECRET_KEY`

## Guardrails

- LLM budget caps should be enforced per run and over time.
- When limits are reached, workflows should skip optional LLM work safely.
- Candidate-specific workflows must fail closed when `skillset.local.md` is unavailable.
