# Agent Factory v0.2 — Checkpoint

## State

v0.2 source package prepared. No live source collection has been performed from this package in the build environment because outbound DNS/network access is unavailable there.

## Completed

- v0.1 converted to v0.2 architecture.
- Source adapters separated for Moltbook and MoltJobs.
- Moltbook source changed to public `/m/rss` discovery surface.
- MoltJobs discovery uses `GET /v1/jobs?status=OPEN&limit=100` and follows `meta.nextCursor`.
- Optional bearer authentication is environment-variable based.
- Added first-class agent/evidence/observation/payment/candidate schema.
- Seed findings are ingested.
- Payment claims and verified payments are structurally distinct.
- OPEN jobs are not treated as agent earnings.
- Stable content hashes and job IDs prevent the v0.1 collision bug.
- Non-ASCII names are preserved.
- Scoring uses word/regex boundaries and separates earning/capability scores.
- Added source validation, source verification command, pagination, indexes and pytest tests.
- Blueprint filename collision protection added.
- No wallet, bidding, spending or autonomous execution code added.

## Current external-source notes

- Moltbook has a public RSS surface at `https://moltbook.com/m/rss`; its current developer material also documents the `/api/v1` API and bearer authentication for authenticated agent operations.
- MoltJobs currently documents public job discovery and an authenticated agent workflow; current public forum material demonstrates `GET /v1/jobs?status=OPEN` and pagination via `meta.nextCursor`.

## Next action

Run locally on Windows:

1. `py -3.12 -m venv .venv`
2. `\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. `\.venv\Scripts\python.exe -m agent_factory init-db`
4. `\.venv\Scripts\python.exe -m agent_factory verify-sources`
5. `\.venv\Scripts\python.exe -m pytest -q`
6. Only after tests/source verification: `\.venv\Scripts\python.exe -m agent_factory scout`

If the conversation is interrupted, return this checkpoint plus the v0.2 zip and continue from the test/source-verification stage. Do not jump to bidding or wallet integration.
