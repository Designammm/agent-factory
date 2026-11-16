# Agent Factory v0.4

Discovery/evidence-analysis prototype for the Agent Factory project.

## V0.4 scope

V0.4 fixes the V0.3 audit blockers and the highest-value follow-ups:

- One shared negation detector is used by scoring, claim classification, and payment-state extraction.
- Negated payment claims are explicitly classified as `negated_claim` and are **not inserted** into the payments table.
- Present-tense and inflected earning/payment forms are handled together.
- `near` is no longer treated as a currency merely because it appears as the English word “near”. NEAR currency detection requires monetary/contextual evidence.
- Author-less evidence never creates a pseudo-agent from a URL path. It remains orphan evidence with explicit `identity_confidence`.
- Work/category matching accepts common morphological variants such as `researcher`, `researching`, `testing`, and `coding`.
- Risk scoring includes credential/security language plus configurable hype/spam density signals.
- Risk can be a configurable candidate gate (`candidate_max_risk`), not only a sorting signal.
- Tests exercise the real database schema, negated payment persistence, pagination/redirect/retry behavior through the source adapters, identity handling, and adversarial scoring.

## Scope boundary

It still does **not** bid, spend money, execute paid work, access a wallet, sign transactions, or perform withdrawals.

A payment claim is not a verified payment. A transaction hash is stored as unverified evidence until an independent verification adapter is added.

## Run

```bat
python -m agent_factory init-db
python -m agent_factory verify-sources
python -m agent_factory scout
python -m agent_factory report
pytest -q
```

Optional credentials:

- `MOLTBOOK_API_KEY`
- `MOLTJOBS_API_KEY`

No private key, seed phrase, or wallet secret belongs in this project.

## V0.4 audit focus

The next audit should specifically verify:

1. Full V0.3 -> V0.4 migration on an existing database.
2. Negated payment claims never enter `payments` and never contribute to aggregates.
3. Present-tense and morphological negation cases.
4. Author-less URL evidence stays orphaned and cannot become a candidate.
5. `near` does not create false earning signals.
6. Risk gate behavior and configurable threshold.
7. Real schema relationship test and source-adapter tests.
8. Live API response shapes when network access is available.
9. Stored external URLs are not automatically followed by any current code path.
