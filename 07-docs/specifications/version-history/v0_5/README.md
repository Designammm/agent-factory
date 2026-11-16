# Agent Factory v0.5.0

Local-first discovery and evidence-analysis core for the Agent Factory project.

## Scope

V0.5.0 is a corrective iteration over V0.4.5, based on its adversarial audit. It fixes the remaining payment-negation and evidence-aggregation defects and tightens earning-claim semantics.

It still does **not** bid, spend money, execute paid work, access a wallet, sign transactions, or perform withdrawals.

## Corrective changes

- Expanded negation handling to `wasn't`, `isn't`, `weren't`, `aren't` and equivalent non-contracted forms.
- Kept negation semantics shared between scoring, payment state, and payment persistence.
- Added intent-vs-completed-claim separation so phrases such as `want to earn`, `jobs can pay`, and `target is 10 USDC` do not become full earning claims.
- Added completed `settled` and `released` payment claims.
- Candidate scoring is now performed per evidence item instead of on a concatenated text blob.
- Earning uses the strongest individual evidence; capability accumulates across independent evidence up to a cap; risk uses the strongest evidence item.
- Added protection against obvious third-party and quoted payment claims being treated as the named agent's earnings.
- Added design/designing/designer capability morphology.
- Hype contributes risk independently of money-word count.
- Replaced the ineffective `impersonat` risk token with explicit variants.
- Added regression tests for the above behaviors.

## Workflow

`DISCOVER → RAW EVIDENCE → IDENTITY RESOLUTION → AGENT ↔ EVIDENCE → OBSERVATION / CLAIM → PAYMENT EXTRACTION → PAYMENT STATE → EARNING + CAPABILITY + RISK → CANDIDATE`

## Important semantics

- A negated payment statement is evidence about a negative claim, not a payment record.
- A payment claim is not a verified payment.
- A transaction-shaped hash is stored as unverified evidence until a later independent verifier exists.
- Evidence without an author is retained as evidence but is not converted into an agent from a URL path.
- A third-party or quoted payment statement is not treated as the named agent's completed earning claim.
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
