# Agent Factory — V0.3 Checkpoint

## Status

V0.3 is implemented locally, tested, and ready for external audit.

## Workflow

`DISCOVER → RAW EVIDENCE → IDENTITY RESOLUTION → AGENT ↔ EVIDENCE → OBSERVATION / CLAIM → PAYMENT EXTRACTION → PAYMENT STATE → EARNING + CAPABILITY + RISK → CANDIDATE`

## Fixed from V0.2

1. Replaced the unverified Moltbook RSS route with the canonical JSON API feed path.
2. Added redirect host validation and retry/backoff for transient HTTP failures.
3. Added `evidence.agent_id` and switched candidate/blueprint relationships away from author-name joins.
4. Wired payment extraction into seed/live evidence ingestion.
5. Separated payment claim, unverified claim, and transaction-present-but-unverified states.
6. Added Ethereum/Base transaction-hash extraction without treating it as verified automatically.
7. Added token/regex matching to remove substring false positives.
8. Added negation handling for common payment claims.
9. Restored active risk scoring.
10. Updated MoltJobs parsing to current-looking fields and cursor pagination with a page cap.
11. OPEN MoltJobs jobs remain demand evidence and do not create fake earning agents.
12. Added verified-payment counters and independent payment metadata.
13. Expanded adversarial tests.
14. Preserved V2 migration compatibility for the local SQLite database.

## External verification used during implementation

Current web evidence confirms Moltbook's `/api/v1` API family and current MoltJobs API/CLI behavior. MoltJobs documentation and recent forum evidence specifically support cursor pagination, a maximum page size of 100, and the distinction between open/funded/settled work. These are implementation inputs, not proof that every local network request will succeed.

## Known remaining boundary

V0.3 deliberately does not independently verify blockchain transactions yet. It records transaction-like evidence and labels it unverified. Independent chain verification should be a separate adapter in a later version so it cannot silently turn a text claim into a verified payment.

## Audit command set

```text
pytest -q
python -m agent_factory init-db
python -m agent_factory verify-sources
python -m agent_factory scout
python -m agent_factory report
```

## Next decision gate

Claude should audit V0.3 before V0.4. Do not add bidding, execution, wallet access, or autonomous spending until the discovery/evidence/payment model passes that audit.

## Local validation performed

- `pytest -q`: 10 passed.
- `init-db`: seed import succeeds.
- `verify-sources`: both live endpoints fail only because this execution environment cannot resolve external DNS; failure is reported cleanly.
- `scout`: continues after both source failures and rebuilds candidates from local seed evidence.
- Payment extraction is idempotent via a deterministic `payment_key`.
