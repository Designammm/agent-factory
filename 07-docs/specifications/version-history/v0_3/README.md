# Agent Factory v0.3

Local-first discovery and evidence-analysis prototype for the Agent Factory project.

## Scope

V0.3 fixes the V2 audit findings around source adapters, evidence identity, payment claims, scoring false positives, risk scoring, MoltJobs pagination, and test coverage.

It still does **not** bid, spend money, execute paid work, access a wallet, or perform withdrawals.

## Sources

- Moltbook: canonical JSON API feed at `/api/v1/feed`.
- MoltJobs: public/open-job discovery through `/v1/jobs`, with cursor pagination and a page cap.

A source failure is isolated and reported as `[WARN]`; the scout can continue with other sources.

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

## Interpretation

Three independent signals are maintained:

- **Earning score:** language/evidence suggesting economic activity.
- **Capability score:** observable work/technical capability.
- **Risk score:** signals requiring rejection or human review later.

A payment claim is not a verified payment. A transaction hash is stored as unverified evidence until independently checked. An OPEN MoltJobs listing is demand evidence, not agent income.

## V3 boundary

The next audit should test the real API response shapes, DB migration from V2, payment-state semantics, rate-limit behavior, and adversarial scoring against fixtures.
