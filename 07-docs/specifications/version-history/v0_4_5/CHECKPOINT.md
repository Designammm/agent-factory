# Agent Factory — V0.4.5 Checkpoint

## Status

V0.4.5 is the corrective build derived directly from the shipped V0.3 source plus the V0.3 adversarial audit findings.

## Corrective changes

1. One shared negation detector is used by scoring and payment-state logic.
2. Present-tense negation and currency-token negation are handled.
3. Negated payment claims are not inserted into `payments`; migration removes provably negated legacy V0.3 rows.
4. URL-only evidence no longer creates pseudo-agents; V0.3 URL-derived pseudo-agents are detached during migration.
5. `identity_confidence` distinguishes author-backed evidence from URL-only evidence.
6. Common capability morphology variants such as `researcher`, `researching`, `tester`, `coding`, and `automation` are recognized.
7. `near` alone is not treated as NEAR currency.
8. API capability is counted once rather than through overlapping work/automation lists.
9. Risk detection includes hype/density signals.
10. Risk gating is configurable through `risk_gate_enabled` and `candidate_max_risk`.
11. The schema relationship tests exercise the real project schema.
12. Duplicate-evidence DB round-trip is tested.
13. Retry, redirect, pagination-cap, and Moltbook parser tests are included.
14. MoltJobs missing-ID dedup uses deterministic SHA-256.
15. No wallet, signing, spending, bidding, paid execution, or withdrawal functionality was added.

## Migration

The database migration is additive. Existing V3 evidence is retained. Only two classes of invalid V3 artifacts are cleaned:
- payment rows whose source evidence is provably negated;
- agents whose canonical identity was fabricated from a URL path when no author existed.

## Validation target

The next external audit should attempt to falsify:
- negation/payment separation;
- identity confidence and orphan handling;
- risk gate semantics;
- scoring false positives/false negatives;
- real schema behavior;
- source adapter behavior;
- migration behavior from V3.

Live API response shapes remain environment-dependent and should be verified where network access is available.

## Local validation performed

- `pytest -q`: 22 passed.
- Fresh `init-db`: seed import 5.
- Fresh `scout`: source failures are isolated in this offline environment; local evidence remains usable and candidates rebuild.
- V3 migration fixture: negated payment row removed; URL-only pseudo-agent removed; evidence retained as `url_only`.
