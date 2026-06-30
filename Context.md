# Head Hunter Context

Head Hunter is a local-first personal job-search agent focused on company discovery, official-source job scanning, role scoring, and review workflows. This repository is intentionally modular so resume-generation and daVinci-related features can be added later without coupling them into the web app, Temporal workflows, or database core.

## Current scope

- Head Hunter only
- Local Flask UI
- SQLite system of record
- Local Temporal orchestration
- Configurable seed and scan policies
- Candidate profile sourced from a local markdown file

## Non-goals in v1

- Resume generation
- Google Drive or Google Docs integration
- daVinci implementation
- Cloud-managed scheduler, queue, or database
- Third-party job-board scraping

## Source-of-truth hierarchy

1. Local configuration files and environment variables
2. Local candidate profile file
3. SQLite persistent state
4. Temporal workflow state

## Extension boundary

Future daVinci integration should consume structured candidate-profile context, selected job records, and scoring data through service boundaries rather than through Flask routes or direct template logic.
