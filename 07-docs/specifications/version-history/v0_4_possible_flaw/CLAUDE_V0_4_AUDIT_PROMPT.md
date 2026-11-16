# Agent Factory v0.4 — Adversarial Audit Request

Audit the attached Agent Factory v0.4 as an adversarial software engineer. Do not modify project files. Run the actual code and tests in the supplied project.

## Context

V0.3 was audited and was NOT READY. The verified blockers were:

1. Negated payment claims such as `I never earned 10 USDC` still created indistinguishable payment rows.
2. `I did not earn 10 USDC` incorrectly crossed the earning threshold.
3. Author-less evidence with a URL created pseudo-agents from URL path segments.
4. Morphological variants such as `researcher` / `testing` caused false negatives.
5. `near` could create a false money signal from ordinary English.
6. Spam/hype language could receive zero risk.
7. Risk was only a ranking signal, not an explicit candidate gate.
8. The schema test used a toy database instead of the real schema.
9. Important retry, redirect, pagination, and migration behaviors lacked direct tests.

## Audit rules

- Do not reward code merely because the function exists. Execute it.
- Do not treat passing unit tests as sufficient. Inspect whether tests exercise the real behavior.
- Distinguish verified behavior from unverified live API behavior.
- Do not modify files.
- Do not silently substitute simulated API results for live verification.
- If network access is unavailable, say exactly what could not be live-verified.

## Required checks

### 1. Runtime
- `python -m pytest -q`
- `python -m agent_factory init-db`
- `python -m agent_factory verify-sources`
- `python -m agent_factory scout`
- `python -m agent_factory report`

### 2. V3 → V4 migration
Create a minimal V3-style database containing:
- a URL-derived pseudo-agent,
- evidence attached to that pseudo-agent,
- a payment row generated from a negated claim.
Run the V4 migration and verify both are cleaned/detached correctly.

### 3. Payment semantics
Test all of these against both scoring and persistence:
- `I earned 10 USDC`
- `I did not earn 10 USDC`
- `I never earned 10 USDC`
- `I do not receive payment`
- `I did not receive payment and there is no transaction proof`
- a genuine transaction-shaped claim with a 64-hex Ethereum/Base tx hash

Verify that negated claims never become positive payment records and never contribute to candidate aggregates.

### 4. Identity
Test:
- named author + URL
- empty author + URL
- empty author + empty URL
- two different author-less URLs

Verify that no URL path becomes an agent name and that author-less evidence cannot become a candidate.

### 5. Scoring adversarial matrix
At minimum test:
- `office near station`
- `Doha, Qatar; base64 encoding`
- `I earned 10 USDC`
- `I did not earn 10 USDC`
- `designer and researcher`
- `Python automation and testing`
- `GUARANTEED USDC Base paid earning wallet automation payout income!!`
- `private key access and wallet credentials`
- `unpaid OPEN job`

Look specifically for false positives, false negatives, double-counting, and brittle tokenization.

### 6. Risk gate
Verify that high-risk candidates are actually excluded when the configured risk gate is enabled, and that the threshold is configurable. Also verify the behavior when the gate is disabled.

### 7. Real schema
Inspect the actual SQLite schema produced by `conn()` and verify:
- foreign keys
- evidence → agent relationship
- identity confidence
- payment state
- payment key uniqueness
- schema version 4

### 8. HTTP safety and resilience
Using mocked HTTP responses, verify:
- retry on 429/5xx is bounded
- redirect to an unallowed host is blocked
- same-host relative redirect is handled safely
- MoltJobs pagination terminates
- MoltJobs pagination exceeding `max_pages` raises
- missing MoltJobs IDs use deterministic hashing

### 9. Source adapters
Inspect and, where network permits, verify the actual Moltbook and MoltJobs response shapes. Do not call a 403/egress-proxy response evidence about the real service.

### 10. Security boundary
Confirm there is still no:
- private key / seed phrase handling
- wallet signing
- autonomous spending
- bidding
- paid execution
- withdrawal
- shell execution
- obvious SQL injection
- path traversal

## Required output

Return a structured audit with:

1. Executive verdict: READY / NOT READY FOR NEXT ITERATION.
2. Runtime results.
3. Verified fixes.
4. Remaining bugs, each with severity, exact reproduction, root cause, and recommended fix.
5. Security findings.
6. Architecture findings.
7. Missing tests.
8. Live API verification status.
9. A prioritized V0.5 plan only if V0.4 is not ready.

Do not edit the repository.
