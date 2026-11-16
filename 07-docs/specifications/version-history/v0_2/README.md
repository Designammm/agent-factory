# Agent Factory v0.2

Local-first research system for discovering AI agents, jobs, capabilities and payment evidence without pretending that public claims are verified earnings.

## What changed from v0.1

- Replaced fabricated Moltbook `/feeds/rss` and `/feeds/atom` configuration with the currently discoverable public Moltbook RSS surface (`/m/rss`).
- Uses MoltJobs public OPEN-job discovery and follows `nextCursor` until the board is exhausted.
- Optional bearer keys are supported through environment variables; no keys belong in `config.json`.
- Added first-class `agents`, `evidence`, `observations`, and `payments` tables.
- Seed findings are actually ingested and retain their confidence/verification caveats.
- OPEN MoltJobs records are treated as demand-side job evidence, not as proof that an agent earned money.
- Replaced substring scoring with token/regex matching.
- Separates `earning_score` from `capability_score`.
- Preserves non-ASCII agent names.
- Uses content hashes and stable IDs instead of fragile URL-only deduplication.
- Adds response validation, source verification, pagination, indexes, and tests.
- Blueprint filenames contain a stable hash to prevent collisions.
- No bidding, wallet control, spending, or autonomous execution is implemented.

## Windows setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m agent_factory init-db
.\.venv\Scripts\python.exe -m agent_factory verify-sources
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m agent_factory scout
.\.venv\Scripts\python.exe -m agent_factory report
```

`verify-sources` and `scout` are allowed to fail a source visibly. A source failure is never treated as proof that there is no data.

## Authentication

MoltJobs public discovery currently works without a key. If an authenticated endpoint is added later, set `MOLTJOBS_API_KEY` as an environment variable.

Moltbook API credentials, if needed for authenticated endpoints later, should be supplied as `MOLTBOOK_API_KEY`. v0.2's public RSS collector does not require a key.

Never put API keys, seed phrases, private keys, or wallet credentials in this project.

## Architecture

```text
Sources
  ├── Moltbook public RSS
  └── MoltJobs public OPEN jobs
          ↓
Evidence (raw observations + confidence)
          ↓
Agents (canonical identities)
          ↓
Observations / Payments
          ↓
Earning score + Capability score
          ↓
Candidate intelligence / rebuild hypotheses
```

The future execution system is intentionally separate from this read-only research layer.
