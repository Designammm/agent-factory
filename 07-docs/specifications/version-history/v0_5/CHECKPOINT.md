# Agent Factory — V0.5.0 Checkpoint

## Basis

V0.5.0 was built directly from the uploaded V0.4.5 project. The external adversarial audit identified six remaining defects/design concerns; this version addresses the payment-negation and aggregation failures plus the principal recommended scoring/risk fixes.

## Corrective changes

1. Expanded the shared negation detector with `was/is/were/are` contractions and equivalent forms.
2. Preserved the rule that negated payment evidence cannot create a payment row.
3. Added completed-claim semantics so intent and targets are not treated as realized earnings.
4. Recognized settled/released payment claims.
5. Reworked candidate scoring to evaluate each evidence row independently; a negated item cannot suppress an unrelated positive item.
6. Earning aggregation uses the strongest evidence item; capability accumulates across evidence with a cap; risk uses the strongest evidence item.
7. Added third-party/quoted-claim protection for obvious cases.
8. Added design morphology variants.
9. Made hype risk contribute independently rather than only when money-word density is high.
10. Replaced the ineffective `impersonat` risk token with explicit variants.
11. Added regression coverage for the above and retained prior V0.4.5 tests.

## Migration

Schema version is 5. The migration remains additive for existing V4 databases; existing evidence is retained. Existing V4 cleanup behavior for provably negated payment rows and URL-derived pseudo-agents remains active.

## Validation performed

- `pytest -q`: 33 passed.
- Fresh `init-db`: 5 seed findings imported.
- Fresh offline `scout`: source failures were isolated; seed evidence remained usable and candidates rebuilt.
- Live Moltbook/MoltJobs behavior was not verified in this environment because external network resolution is unavailable.

## Remaining external verification

- Live Moltbook `/feed` response shape.
- Live MoltJobs `/jobs` wrapper and pagination fields.
- Real-world rate limits and redirect behavior.
- Independent blockchain verification of transaction hashes.
