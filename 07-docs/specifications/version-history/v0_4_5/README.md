# Agent Factory v0.4.5

Local-first discovery and evidence-analysis core for the Agent Factory project.

## Scope

V0.4.5 is a corrective iteration over the shipped V0.3 code and the adversarial V0.3 audit.

It fixes payment-negation consistency, URL-only identity fabrication, capability morphology gaps, risk detection/gating, real-schema test coverage, pagination/redirect/retry test coverage, and deterministic MoltJobs fallback keys.

It still does **not** bid, spend money, execute paid work, access a wallet, sign transactions, or perform withdrawals.

## Workflow

`DISCOVER → RAW EVIDENCE → IDENTITY RESOLUTION → AGENT ↔ EVIDENCE → OBSERVATION / CLAIM → PAYMENT EXTRACTION → PAYMENT STATE → EARNING + CAPABILITY + RISK → CANDIDATE`

## Important semantics

- A negated payment statement is evidence about a negative claim, not a payment record.
- A payment claim is not a verified payment.
- A transaction-shaped hash is stored as unverified evidence until a later independent verifier exists.
- Evidence without an author is retained as evidence but is not converted into an agent from a URL path.
- Risk gating is explicit and configurable.
- OPEN MoltJobs listings are demand evidence, not agent income.

## Sources

- Moltbook: `/api/v1/feed?sort=new&limit=N`.
- MoltJobs: `/v1/jobs` with cursor pagination and a bounded page count.

Source failures are isolated and reported; local/seed evidence remains usable.

## Run on Windows

```bat
python -m agent_factory init-db
python -m agent_factory verify-sources
python -m agent_factory scout
python -m agent_factory report
pytest -q
```

Optional credentials are environment variables:

- `MOLTBOOK_API_KEY`
- `MOLTJOBS_API_KEY`

No private key or wallet secret belongs in this project.
