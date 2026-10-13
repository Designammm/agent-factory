# Agent Factory v0.7.0 — Independent Adversarial Audit

Auditor: Claude (Agent Factory HQ test chat). Date: 2026-10-13.
Code changed: **NO**. All tests ran on temporary copies and temporary databases outside the project.

Evidence labels: **EXEC** = confirmed by execution. **CODE** = confirmed by code inspection. **INFER** = inferred. **UNVER** = unverified. **NOT TESTED**. **ENV** = blocked by environment.

---

## 1. Executive Summary

**Verdict: BLOCKED — MUST FIX.**

The v0.7 fixes for the five v0.6 findings are real but incomplete. Four things were confirmed by execution:

1. **Secret-solicitation text does not trip the risk gate.** `seed phrase`, `secret key`, `wallet credentials`, `api key` all score risk 5. The gate is `risk > 6`. They pass. `mnemonic` and `wallet secret` score 0. `private key` is blocked only because it is counted twice (2+5=7). (BUG-1)
2. **The negation matcher suppresses genuine claims.** 14 of 14 benign sentences ("I earned 10 USDC, no joke.") became `negated_claim`. (BUG-2)
3. **The payment ledger can store wrong amounts.** `I earned 12,500.50 USDC` stores **500.5**. (BUG-4)
4. **Candidate selection still uses claims that have no valid payment.** `I earned 0 USDC.` scores earning 7 and becomes a candidate with 0 payments. `I earned nothing.` scores 4 and becomes a candidate. A third-party claim plus a tx-shaped string scores 4 and becomes a candidate. (BUG-5, BUG-8)

What is good (EXEC): no wallet, signing, spending, shell, eval or pickle code exists. SQL is parameterised. Plain re-ingestion is idempotent. Candidate scores do not depend on evidence order (120 permutations, one outcome). `verified` can never be produced by code. A source failure does not stop the other source.

Live Moltbook/MoltJobs compatibility: **UNVER — ENV** (proxy returned 403 on tunnel). This is not a software failure.

---

## 2. Test Environment

| Item | Value |
|---|---|
| OS | Linux 6.18.44 x86_64 (cloud container) |
| Python | 3.13.16 |
| SQLite | 3.45.1 |
| pytest | 8.4.2 |
| requests / bs4 | 2.34.2 / 4.15.0 |
| Package folder in zip | `agent_factory_v0_6/` (contents are v0.7.0) |
| Network | Outbound to moltbook.com and moltjobs.io blocked (ENV) |

Fixtures: `HTTP` was mocked at `requests.get`. The "legacy schema" DB in BUG-18 is **my reconstruction** from the migration branches in `conn()`. It is not a real v3 DB (INFER).

---

## 3. Existing Test Suite Results

Command: `python -m pytest -q -p no:cacheprovider` (in a copy).

- Collected 43. Passed 43. Failed 0. Skipped 0. Errors 0. Time 0.28 s. **EXEC**
- `-W error` run fails with `PytestUnraisableExceptionWarning` (unclosed `sqlite3.Connection`). **EXEC** (BUG-19)
- Side effect: the suite created `data/agent_factory.db` and `data/raw/` inside the project folder. `test_current_version_is_used_in_cli_banner` calls the real `scout()` on the real DB path. **EXEC** (BUG-19)

Blind spots (CODE): no test for text with both a claim and a negation word; no test for thousands separators; no test for amounts with no currency; no test for names as third parties; no test for edited posts; no test for the migration; no test for adapters beyond 7 cases; no test for secret terms other than `private key`; no boundary test for risk 6 vs 7. Every "intent" and "third-party" test uses one short sentence. Tests assert the fixed examples from the v0.6 audit, not the class of bug.

---

## 4. CLI Execution Results

Commands (from `__main__.py`): `init-db`, `verify-sources`, `scout`, `report`. Run on a fresh copy.

| Step | Result | Label |
|---|---|---|
| `init-db` | Seed imported: 5 | EXEC |
| `init-db` again | Seed imported: 0 | EXEC |
| `scout` x2 | Banner `v0.7.0`. Both sources WARN (proxy 403). Counts same both runs: evidence 5, agents 5, candidates 3. About 10 s per run (retry back-off). | EXEC |
| DB after both runs | agents 5, evidence 5, observations 5, payments 1, candidates 3 | EXEC |
| `report` | 3 candidates printed | EXEC |
| `verify-sources` | `[FAIL]` both, network | EXEC / ENV |

Repeated `scout` created no duplicates. Plain `collect()` twice with mocks: counts equal. **EXEC**

---

## 5. Core Pipeline Test

Chain: SOURCE → evidence (`insert_evidence`) → identity (`upsert_agent`) → observation → payment (`extract_and_store_payments`) → scoring (`score_evidence`) → candidate (`candidate_rows`).

- Identity key is `author:<casefold>`. No author → no agent, evidence kept with `agent_id` NULL. **EXEC**
- MoltJobs jobs never get an agent and never produce payments, even if the title says "I earned 10 USDC". **EXEC**
- Malformed input: NUL characters stored without error. Text over 100 000 chars truncated for storage. Hash uses the full text. **EXEC**
- Three components decide "is this a claim" with three different rules: `classify_claim` (observations), `payment_state` (ledger), `score_evidence` (score). They disagree (BUG-15).

---

## 6. Payment / Earning Tests

Positive forms (`earned`, `was paid`, `received`, `made`, `got paid`) → `claim`. **EXEC**
Negated forms in the prompt list (all 7) → `negated_claim`, score 0. **EXEC**
Intent forms in the prompt list (all 6) → `non_claim`, score 2. **EXEC**
Third-party forms in the prompt list (all 9) → `non_claim`, score 2. **EXEC**

Failures found:

| Input | Actual | Problem |
|---|---|---|
| `I earned 0 USDC.` / `I received -1 USDC.` | state `claim`, score **7**, no ledger row | Candidate with 0 payments (BUG-5) |
| `I earned 1,000 USDC` | amount 0.0, score 7 | BUG-4 |
| `I earned 12,500.50 USDC` | **ledger stores 500.5** | BUG-4 |
| `I earned 1.000 USDC` | amount 1.0 | BUG-4 |
| `I earned nothing.` | `claim`, score 4 → candidate | BUG-5 |
| `Got paid!` / `I received a payout.` | `claim`, score 4, no amount → candidate | BUG-5 |
| `Alice earned 10 USDC.` | `claim`, ledger row 10.0 | BUG-6 |
| `Bob received 10 USDC.` / `The bot earned` / `This agent earned` / `We earned` | `claim` | BUG-6 |
| `Congrats to Bob who earned 10 USDC!` | `claim` | BUG-6 |
| `Thanks @bob! I earned 10 USDC.` | `non_claim` (own claim lost) | BUG-7 |
| `I earned 10 USDC but my friend earned 20 USDC.` | `non_claim` | BUG-7 |
| `I earned 5 USDC. I did not earn 10 USDC.` | `negated_claim`, score 0 (both orders) | BUG-2 |
| `I earned 10 USDC, no joke.` (+13 more) | `negated_claim` | BUG-2 |
| `If I earned 10 USDC I would be happy.` | `claim` | BUG-16 |
| `Have you earned 10 USDC?` / `Imagine I earned…` / `I earned 10 USDC (fake).` | `claim` | BUG-16 |
| `"I earned 10 USDC"` (quote marks only) | `claim` | BUG-7 |

Formats (EXEC): `10 USDC`, `10.5 USDC`, `0.50 USDC`, `10 USD`, `10 USDT`, `10usdc`, `10 USDC.` and `10 USDC / task` are accepted. `$10`, `USD 10`, `USDC 10`, `10 DAI`, `10 EUR`, `10 ETH`, `ten USDC`, `1e3 USDC` give **no amount**, but the claim still scores 4. Only the first amount in a text is kept (`10 usdc and 5 usdt` → one row).

Note: "I earned 10 USDC; they paid me." → `claim`. Correct.

---

## 7. Transaction Verification

- `"verified"` is **never assigned** by any executable code. Only comparisons and the schema default exist (grep, whole repo). **VERIFICATION NOT IMPLEMENTED / UNVER.** This matches the README. Not a bug.
- Payment states that code can produce: `claim`, `evidence_pending_verification` (stored); `non_claim`, `negated_claim` (computed, not stored). `tx_present_unverified` and `unverified` are `verification` values. **EXEC**
- Hash shape: `0x`+64 hex, any case → accepted. Short, no `0x`, non-hex, 65 chars → rejected. With punctuation → accepted. **EXEC**
- A valid-shaped hash with a completed claim → `evidence_pending_verification` / `tx_present_unverified`. Never `verified`. **EXEC** Invariant holds.
- Same hash, two agents → two ledger rows. Same hash, upper and lower case → another row. No unique key on `tx_hash` (BUG-12).
- `payments.verification` and `payment_state` have no CHECK constraint. A `verified` row can be inserted by hand. **EXEC**
- Latent: if a verifier is added later, `conn()` can delete verified rows (BUG-3).

---

## 8. Capability Detection

- Substring collisions rejected: `discontent`, `designated`, `testing123`, `metadata`. **EXEC**
- All prompt variants score capability 2 (`design*`, `write*`, `code*`, `research*`, `automat*`, `copywrit*`, `programm*`). `automatedly` works. **EXEC**
- Not recognised (no capability): `developer`, `developing`, `engineer`, `translator`, `analyst`. These are not documented as supported. NOTE only.
- **Two vocabularies disagree (BUG-14).** `category_set` returns `unknown` for `designer`, `design`, `write`, `writer`, `writing`, `copywriter`, `programmer`, `programming`, `automation`, `researchers`, `documenting`, `extract`. Scoring accepts them all. `copywriting` → `content`, but `copywriter` → `unknown`.
- False positives, capability 2 each: `code of conduct`, `by design`, `I lead a team`, `I am content with life`, `report abuse` (BUG-21).
- Capability sums across evidence (cap 20). An agent with two generic posts reaches the capability threshold 3 with earning 0. **CODE**

---

## 9. Risk System

Per-term risk (EXEC):

| Term | Risk | Note |
|---|---|---|
| `trading`, `gambling`, `fake review`, `testimonial`, `impersonate`, `credential`, `password` | 2 each | exact form only |
| `private key` | **7** | flat 2 + regex 5 = double count |
| `seed phrase`, `secret key`, `api key` | 5 | regex only |
| `wallet credentials` | 5 | |
| `wallet credential` | **7** | flat `credential` 2 + regex 5 |
| `login credential` / `login credentials` | 7 / 5 | same pattern |
| `mnemonic`, `wallet secret` | **0** | not in any list |
| `impersonate/-d/-ion/-ing/-or` | 2 | v0.7 fix works |
| `impersonates`, `impersonators`, `impersonations` | **0** | |
| `fake reviews`, `testimonials`, `passwords`, `credentials`, `trader`, `gamble` | **0** | plurals/inflections |
| `guarantee`, `guarantees`, `instantly`, `get-rich-quick`, `passive-income` | **0** | no hype variants |
| `100%` (any context: `100% legit`, `100% sure`) | **0** | dead entry; `\b` after `%` never matches before a space (BUG-9) |
| `pr1vate key`, `private-key`, `seedphrase` | 0 | obfuscation, NOTE |

Combinations (EXEC):
- `I earned 10 USDC and this is guaranteed passive income.` → risk 7. Gated.
- `I earned 10 USDC, guaranteed.` → risk **5**. Not gated (one hype word + claim).
- `guaranteed instant easy money passive income get rich free money` → risk 6. Hype is capped at 6. **Hype alone can never cross a gate of 6** (BUG-10).
- Risk is the **max** over evidence, not the sum. Three posts of risk 6 → risk 6, included. **EXEC**
- Independent signals add up within one text and never reduce risk. **EXEC** (invariant holds)
- Risk lowers rank only as the third sort key. **CODE**

---

## 10. Risk Gate Boundary

Threshold `candidate_max_risk = 6`. Rule is `risk > 6` (strict). **EXEC** through `candidate_rows`:

| risk | included |
|---|---|
| 4 | yes |
| 5 | yes |
| 6 (= threshold) | yes |
| 7 (= threshold + 1) | no |
| 8 | no |

A gated agent is **removed from candidates entirely**. With `risk_gate_enabled=false` it is included and `risk_score` is still reported (11 in the test). **EXEC**

---

## 11. Identity Resolution

- Author + URL → agent. Missing author → no agent. Whitespace author → no agent. URL-only → **no pseudo-agent** (3 evidence rows with NULL agent). **EXEC**
- Same author, different URLs → one agent. `Alice` and `alice` → one agent. **EXEC**
- Different authors, same URL → two agents. **EXEC**
- No Unicode normalisation: `José` (precomposed) and `José` → **two agents**. `a​b` ≠ `ab`. **EXEC**
- Key has no source prefix: `alice` on Moltbook and `alice` on MoltJobs merge. **EXEC**
- `None`, `null` become agents. `unknown-agent` is excluded but `Unknown-Agent` is not. Moltbook author as a list becomes the agent `['a']`. **EXEC** (BUG-13)
- Seed file creates "agents" named `MoltJobs marketplace` and `Moltbook agent-finance discussion`. **EXEC** (BUG-22)

---

## 12. Evidence Aggregation

- 5 texts (positive, negative, third-party, capability) in all 120 orders → **one** result. **EXEC**
- Mixed agents: a negation by agent B does not suppress agent A. A friend's claim does not leak. **EXEC**
- Cross-contamination **inside one text** is not solved: `I earned 5 USDC. I did not earn 10 USDC.` → whole text negated (BUG-2). `I earned 10 USDC.\n> he earned 5 USDC` → whole text dropped (BUG-7).
- Contradiction across evidence: a stored payment is kept even if another post negates it. Design choice. NOTE.

---

## 13. Database Integrity

- Schema: 6 tables, FKs on, WAL on. `UNIQUE(source,content_hash)`, `UNIQUE(agent_id,evidence_id,claim_type)`, `UNIQUE(payment_key)`, `UNIQUE(agent_id)` on candidates. **EXEC**
- Bogus `agent_id` insert rejected (FK works). **EXEC**
- Delete agent → observations and candidates cascade. `payments` and `evidence` keep the row with `agent_id` NULL (orphan payment). **EXEC**
- Edited post (same `external_id`, new text) → second evidence row and **second payment**. **EXEC** (BUG-12)
- Same text, different authors, empty id and url → hash ignores author. Second author's payment links to the first author's evidence row. Ledger has a row for an agent that has no evidence. **EXEC** (BUG-11)
- `conn()` re-scans all payments and deletes negated ones **on every connection**, including `verified` rows. **EXEC** (BUG-3)
- Connections are never closed. **CODE**
- Legacy migration: see BUG-18.

---

## 14. Source Adapter Testing

All HTTP mocked. Live calls: **ENV**.

| Case | Result | Label |
|---|---|---|
| Moltbook malformed JSON / wrong type / no list / no usable posts | raises, caught in `collect()` | EXEC |
| Moltbook empty feed | raises `zero usable posts` (an empty feed counts as failure) | EXEC |
| Moltbook author as list | agent `['a']` | EXEC |
| MoltJobs non-JSON content-type, list payload, data not a list | raises | EXEC |
| MoltJobs duplicate ids in page | de-duplicated | EXEC |
| MoltJobs 21 distinct pages | 20 requests, then `RuntimeError`; **all fetched jobs discarded** (BUG-17) | EXEC x2 |
| MoltJobs same cursor forever | stops at 20, same discard | EXEC |
| HTTP 404 / 500 | retried, `SourceError` | EXEC |
| 429 then 200 | retried, OK | EXEC |
| Redirect to other host / http | blocked | EXEC |
| Redirect chain (302→302) | second 3xx returned as OK (fails later at `.json()`) | EXEC |
| Timeout | `SourceError` | EXEC |
| Allowlist: look-alike host, userinfo trick, file://, 127.0.0.1 | blocked | EXEC |
| Allowlist: port 8443, upper-case host | allowed (host check ignores port) | EXEC (BUG-24) |
| Cursor with `&` `#` | URL-encoded correctly | EXEC |
| One source fails, other works (both directions) | other source still stored | EXEC |

---

## 15. Security Review

Grep for `subprocess`, `shell=True`, `os.system`, `eval(`, `exec(`, `pickle`, `mnemonic`, `seed phrase`, `private key`, `withdraw`, `web3`, signing: **no executable hit.** Only the risk-word regexes match. **CODE**

- SQL: all values passed as parameters. No f-string SQL. **CODE**
- Path: report file name = slug + SHA-1 of id/name; hostile name `../../etc/passwd` stayed inside `reports/`. **EXEC**
- SSRF: fetch only to two hard-coded hosts over HTTPS. Evidence text is never fetched. **CODE**
- Secrets: only `MOLTBOOK_API_KEY` and `MOLTJOBS_API_KEY` read from env. Sent as `Authorization` to allow-listed hosts only. Not stored. **CODE**
- External text stays data in the DB. **But** reports embed raw name, title and text in Markdown. A hostile name injected a `# SYSTEM:` heading; a hostile text injected `## NEW INSTRUCTION`. **EXEC** (BUG-23). If a later stage feeds reports to a model, this is a prompt-injection path. **INFER**

---

## 16. Wallet / Payment Safety

- No private key, seed phrase, mnemonic or wallet secret is read, stored or written. **CODE**
- No signing, spending, withdrawal or bid code. No public receiving address in the code or the config. **CODE**
- Trust Wallet routing described in the project description is **not implemented**. NOT TESTED / by design.
- The project's own safety list (private key, seed phrase, mnemonic, wallet secret) is not enforced on incoming text (BUG-1).

---

## 17. Configuration Consistency

- `_validate_config()` stops overlap between a flat list and its variant map. Works for the two maps that exist. **EXEC** (in tests and by import)
- `money` and `sources` in `config.json` are **never read** (dead). Adapters hard-code URL, limit and hosts. **CODE**
- Money vocabulary is hard-coded in at least six regexes (`_PAYMENT_TARGET`, `classify_claim`, `score_evidence` x3, `_third_party…`). They differ from each other and from `config["money"]`. **CODE**
- `risk_hype` has no variant map. `risk` has one (`impersonate`) for 8 terms. **CODE**
- `thresholds.risk_gate_enabled` and `candidate_max_risk` are read. `earning_min`, `capability_min` are read. **CODE**
- Version strings: `config.version` 0.7.0, banner 0.7.0, User-Agent 0.7.0, argparse 0.7.0 — match. `agent_factory/__init__.py` says **0.2.0**. README says "hardening over V0.4.5". CHECKPOINT says "schema version 6" (code: 7) and "Built from v0.5.0". Folder name says v0_6. README has v0.6 and v0.7 sections stacked. `requirements.txt` lists `beautifulsoup4`, never imported. (BUG-20)

---

## 18. v0.6 Regression Matrix

| # | Guarantee | Result | Label |
|---|---|---|---|
| 1 | Negated claims not stored | Holds for all listed forms. Over-blocks genuine claims (BUG-2). | EXEC |
| 2 | Present-tense negation | Holds (`don't get paid`, `isn't paid`) | EXEC |
| 3 | Contracted negation | Holds | EXEC |
| 4 | No URL-only pseudo-agents | Holds | EXEC |
| 5 | Capability morphology | Holds for scoring. Fails in `category_set` (BUG-14). | EXEC |
| 6 | No API/source double count | Holds (`API automation` = 3) | EXEC |
| 7 | Hype risk contributes | Holds. Gaps: no variants, `100%` dead (BUG-9) | EXEC |
| 8 | Gate boundary | Holds (`>`, 6 in, 7 out) | EXEC |
| 9 | tx-shaped hash unverified | Holds | EXEC |
| 10 | Ingestion idempotent | Holds for identical re-run. Fails for edited post and same tx (BUG-11, 12). | EXEC |
| 11 | No cross-evidence contamination | Holds across items. Fails inside one text (BUG-2, 7). | EXEC |
| 12 | Intent ≠ earning | Holds for listed forms. Fails for conditional/question (BUG-16). | EXEC |
| 13 | Third-party and quoted excluded | Holds for pronouns, `@handle`, `>` quote. Fails for names, `this agent`, `we`, quote marks (BUG-6, 7). | EXEC |
| 14 | Impersonation consistent | Holds for 5 forms. Fails for `impersonates/-ors/-ions` (BUG-9). | EXEC |
| 15 | Claim + hype escalation | Holds for 2+ hype terms. One hype term + claim = 5, passes gate. | EXEC |

v0.7 changelog claims vs result:
- "Zero and negative amounts do not become payment records" — true for the ledger. **False for candidacy** (BUG-5).
- "@handle detection" — true for `@x earned`. Wrong when `@x` comes before the author's own claim (BUG-7).
- "copywriting/copywriter" — scoring yes. `category_set` no (BUG-14).
- "Test suite: 43 passed" — confirmed.
- "No wallet signing…" — confirmed.

---

## 19. Adversarial Combination Tests

| Input | Result |
|---|---|
| `@other_agent earned 100 USDC, guaranteed passive income.` | `non_claim`, earning 2, risk 4 |
| `Another agent said I earned 50 USDT instantly.` | `non_claim`; `instantly` risk 0 |
| `I never earned 0 USDC but my friend earned 20 USDC.` | `negated_claim`, no row. OK. |
| `I was paid 10 USDC. This is 100% guaranteed easy money.` | `claim`, risk 7. Gated. (`100%` contributes 0; gated by `guaranteed`+`easy money`+3.) |
| `@agent was paid 10 USDC. tx 0x<64>` | `non_claim`, no ledger row, **earning 4 → candidate** (BUG-8) |
| `My friend earned 10 USDC. tx 0x<64>` | same: **candidate** |
| `Bounty: 10 USDC tx 0x<64>` | earning 4 → candidate |
| `I want to earn 100 USDC. My friend already earned 20 USDC.` | `non_claim` |
| `I earned 10 USDC. Send me your seed phrase.` | claim, risk 5, **in candidates** (BUG-1) |
| `Alice earned 10 USDC.` posted by agent `eve` | ledger row 10.0 under `eve` (BUG-6) |

---

## 20. Newly Discovered Bugs

Each bug: Code changed = NO. Reproduce with `score_evidence(text)`, `payment_state(text,None)`, or `candidate_rows(conn)` on a temp DB.

**BUG-1 — Secret-solicitation terms do not gate** · HIGH
- Component: `core.py score_evidence` lines 339–347; `config.json risk`.
- Repro: `score_evidence("I earned 10 USDC. Send me your seed phrase. automation")` → risk 5. `candidate_rows` includes the agent. Same for `secret key`, `wallet credentials`, `api key`. `mnemonic`, `wallet secret` → 0.
- Expected: any request for a private key, seed phrase, mnemonic or wallet secret crosses the gate.
- Root cause: regex adds 5; gate needs >6. `private key` also sits in the flat list (2), so it gets 7 by double count. Plural `credentials` does not match the flat `credential`. Two terms are in no list.
- Impact: a phishing agent that mentions earnings becomes a candidate.
- Fix: one table `secret_terms` with variants and plurals, weight ≥ gate+1 (or a hard-block flag, not a score). Remove `private key` from the flat list. Add `mnemonic`, `recovery phrase`, `wallet secret`, `seed-phrase`.
- Evidence: EXEC x3 (probe runs on different texts and through `candidate_rows`).

**BUG-2 — Negation matcher suppresses genuine claims** · HIGH
- Component: `core.py _NEGATION`, `_PAYMENT_TARGET`, `is_negated_payment_claim` lines 192–201.
- Repro: `payment_state("I earned 10 USDC, no joke.", None)` → `negated_claim`. 14/14 benign variants fail (`not bad`, `no complaints`, `cannot believe it`, `without a hitch`, `No way! I earned…`, `(no tx yet)`).
  `payment_state("I earned 5 USDC. I did not earn 10 USDC.", None)` → `negated_claim`, score 0 (both orders).
- Expected: negation applies to its own clause. Genuine claim in another clause stays.
- Root cause: window of 45 chars before and 25 chars after, no sentence or clause boundary, and `usd`/`usdc`/`near`/`tx`/`hash` are "payment targets".
- Impact: real earnings dropped from ledger and score. Same function is used in three places, so the error is consistent but wrong.
- Fix: split into sentences/clauses first. Negation must be a verb-negation of the payment verb (`did not earn`, `never received`, `was not paid`). Remove `usdc`, `near`, `tx`, `hash` from targets. Add tests with benign negation words.
- Evidence: EXEC (2 probe files, 14 cases).

**BUG-3 — `conn()` deletes payments on every connection** · HIGH (latent)
- Component: `core.py conn()` lines 102–105.
- Repro: insert a payment with `verification='verified'` linked to evidence "I did not earn 10 USDC". Open `core.conn()` again → 0 rows.
- Expected: a migration runs once, guarded by `schema_version`. It never deletes `verified` rows.
- Root cause: clean-up code is in the connect path, not in a versioned migration.
- Impact: today, silent loss of valid claim rows when BUG-2 misreads text. After a verifier exists: loss of verified payments.
- Fix: run clean-up only when stored `schema_version` < 7. Never delete; set `payment_state='negated_claim'` instead.
- Evidence: EXEC (hand-made row).

**BUG-4 — Amount parser breaks on thousands separators** · HIGH
- Component: `core.py _money_amount_re`, `extract_payment`.
- Repro: `extract_payment("I earned 12,500.50 USDC")` → 500.5. `"1,000 USDC"` → 0.0. `"1.000 USDC"` → 1.0. End-to-end: ledger row 500.5.
- Expected: 12500.50, 1000 (or reject as ambiguous).
- Root cause: lookbehind `(?<![\w-])` allows `,` before `000`; `\d+` starts after the comma.
- Impact: wrong money in the ledger; zero amounts dropped while score stays 7.
- Fix: parse `\d{1,3}(,\d{3})*(\.\d+)?|\d+(\.\d+)?`. Reject a number touching `,` or `.` + digit on the left. Reject ambiguous `1.000`.
- Evidence: EXEC x2.

**BUG-5 — Claims without a valid ledger amount still score as strong earnings** · HIGH
- Component: `score_evidence` lines 311–327; `candidate_rows` thresholds.
- Repro: `I earned 0 USDC.` → earning 7. `candidate_rows` includes the agent, `payment_count` 0. `I earned nothing.` → 4, candidate. `Got paid!` → 4, candidate. `I made $5000 yesterday.` → 3.
- Expected: a claim without a ledger-valid amount cannot reach `earning_min`.
- Root cause: score and ledger use different amount checks. v0.7 fixed only the ledger.
- Impact: candidate list contains agents with no payment evidence.
- Fix: compute `amount` once; score `payment-claim` +3 only if `amount > 0`. Add `nothing`, `no money`, `zero` to negation. Support or explicitly reject `$` amounts.
- Evidence: EXEC x3.

**BUG-6 — Third-party detection is a pronoun whitelist; names pass as the author's claim** · HIGH
- Component: `core.py _third_party_or_quoted_claim` lines 233–240.
- Repro: agent `eve` posts `Alice earned 10 USDC.` → ledger row 10.0 under `eve`, score 7. Also `Bob received 10 USDC.`, `The bot earned…`, `This agent earned…`, `We earned…`, `Congrats to Bob who earned…`.
- Expected: only a first-person subject (`I`, `I've`, `my agent` …) makes a completed claim.
- Root cause: blacklist cannot list all names.
- Impact: payment ledger and candidate list attribute others' income to the author.
- Fix: invert the rule. Require first-person subject within the same clause as the verb. Treat everything else as `non_claim`.
- Evidence: EXEC x2.

**BUG-7 — Own claim dropped by a nearby mention or quote** · MEDIUM
- Component: same function, `@handle` branch and `>` branch.
- Repro: `Thanks @bob! I earned 10 USDC.` → `non_claim`. `I earned 10 USDC but my friend earned 20 USDC.` → `non_claim`. `I earned 10 USDC.\n> he earned 5 USDC` → `non_claim`. `"I earned 10 USDC"` (quotes only) → `claim`.
- Root cause: regex runs on the whole text. `.{0,35}` bridges clauses.
- Impact: false negatives; quote marks not handled.
- Fix: evaluate per clause (see BUG-6). Strip quoted lines before evaluation. Treat `"…"` as quoted.
- Evidence: EXEC x2.

**BUG-8 — `transaction-context` score ignores claim state** · HIGH
- Component: `score_evidence` line 326.
- Repro: `@agent was paid 10 USDC. tx 0x<64 hex>` posted by `eve` → earning 4 → candidate. Same for `My friend earned 10 USDC. tx 0x…` and `Bounty: 10 USDC tx 0x…`.
- Expected: invariant "third-party claim must not become the current agent's earning claim".
- Root cause: +2 given when `tx` word and amount/hash appear, with no check of `completed_claim`.
- Impact: third-party and non-claim texts pass `earning_min` (4).
- Fix: add `completed_claim` to the condition.
- Evidence: EXEC x3.

**BUG-9 — Risk morphology: only `impersonate` has variants; `100%` is dead** · MEDIUM
- Component: `config.json risk`, `risk_hype`, `risk_variants`; `score_evidence` lines 339–350.
- Repro: risk 0 for `impersonates`, `impersonators`, `fake reviews`, `testimonials`, `passwords`, `credentials`, `gamble`, `trader`, `guarantee`, `instantly`, `get-rich-quick`, `passive-income`. `100% legit` → 0.
- Root cause: exact `\b` match; `\b100%\b` needs a word character after `%`.
- Impact: the v0.6 morphology problem is fixed for one term only.
- Fix: variant map for every risk and hype term. Match `100\s?%` with a custom lookahead. Reuse `_validate_config` for all maps.
- Evidence: EXEC x2.

**BUG-10 — Hype can never cross the gate alone; one hype word + claim passes** · MEDIUM
- Component: `score_evidence` lines 349–358; `thresholds.candidate_max_risk`.
- Repro: all hype terms in one text → risk 6 (cap) → included. `I earned 10 USDC, guaranteed.` → 5 → included. Three posts with risk 6 → risk 6 → included.
- Root cause: hype cap (6) equals the gate. Risk uses max over evidence.
- Impact: strong hype stays visible as a candidate. README says "strong hype crosses the gate" — only true for 2+ terms with a claim.
- Fix: decide the policy. Either raise the cap above the gate or make the gate a rule (`hype_count >= 2`). Consider summing risk across distinct evidence.
- Evidence: EXEC.

**BUG-11 — Evidence hash ignores author; ledger links to another agent's evidence** · MEDIUM
- Component: `insert_evidence` line 154; `collect()` lines 460–463.
- Repro: two posts, same text, empty `external_id` and `url`, authors `victim` and `copycat` → 1 evidence row (owner `victim`), 2 payment rows. `copycat` has a payment and no evidence.
- Root cause: `content_hash` = source + external_id + url + title + text. `collect()` uses the returned id of the existing row.
- Impact: payment rows without matching evidence; wrong `evidence_count` vs `payment_count`.
- Fix: add canonical author to the hash, or require `external_id`. Only write observation/payment when `created` is true or the evidence owner equals the agent.
- Evidence: EXEC.

**BUG-12 — Payment duplicates for edited posts and shared tx hash** · MEDIUM
- Component: `insert_evidence`; `payments` schema; `payment_key` (line 279).
- Repro: same `external_id`, text edited → 2 evidence rows, 2 payments, `payment_count` 2. Same tx hash by `p1`, `p2`, and again in upper case by `p1` → 3 rows.
- Root cause: key includes `evidence_id` and raw hash case. No unique on `tx_hash`. No update-by-`external_id`.
- Impact: ledger inflation; one tx can back many claims.
- Fix: lower-case the hash. Key payments by (source, external_id) and update on edit. Flag a tx hash seen under more than one agent.
- Evidence: EXEC x2.

**BUG-13 — Identity key weaknesses** · MEDIUM
- Component: `canonical_agent`, `upsert_agent`; `moltbook._author`.
- Repro: see section 11.
- Fix: NFKC-normalise, strip zero-width characters, prefix key with source, reject `none/null/unknown*` case-insensitively, reject non-string authors.
- Evidence: EXEC.

**BUG-14 — Two keyword systems disagree** · MEDIUM
- Component: `category_set` lines 367–378 vs `config.json work_variants`.
- Repro: `category_set("designer")` → `['unknown']` while capability is 2. Same for `writer`, `copywriter`, `programmer`, `automation`, `researchers`, `documenting`.
- Fix: build `category_set` from the same config.
- Evidence: EXEC.

**BUG-15 — Three claim classifiers disagree** · MEDIUM
- Component: `classify_claim` vs `payment_state`.
- Repro: `My friend earned 10 USDC.` → observation `payment_claim`, ledger `non_claim`. Same for `I want to earn 10 USDC.` and `@agent was paid 10 USDC.`
- Impact: `observations` table says the agent made a payment claim when the ledger says it did not.
- Fix: one function returns the state; the others read it.
- Evidence: EXEC.

**BUG-16 — Conditional, hypothetical and question forms read as completed claims** · MEDIUM
- Repro: `If I earned 10 USDC I would be happy.`, `Have you earned 10 USDC?`, `Imagine I earned…`, `Suppose…`, `Pretend…`, `I wish I earned…`, `I earned 10 USDC (fake).` → `claim`.
- Root cause: the intent regex needs the modal **before** the verb; `?` and `if/imagine` are not checked.
- Fix: reject sentences with `?`, `if`, `imagine`, `suppose`, `pretend`, `wish`, `would`, `fake`.
- Evidence: EXEC.

**BUG-17 — Pagination cap discards all fetched jobs** · LOW–MEDIUM
- Component: `moltjobs.pages` line 42; `collect()`.
- Repro: mock 21 distinct pages → 20 requests, `RuntimeError`, 0 jobs stored. Same with a repeated cursor.
- Impact: with more than 2 000 OPEN jobs the source gives nothing, forever.
- Fix: return partial results plus a `truncated` flag and log it.
- Evidence: EXEC x2. Also: empty Moltbook feed raises (LOW).

**BUG-18 — Legacy migration crashes on duplicate payment rows and leaves a half-migrated DB** · LOW–MEDIUM
- Component: `conn()` lines 85–94.
- Repro (synthetic legacy DB with two identical `payments` rows): run 1 → `IntegrityError: UNIQUE constraint failed: payments.payment_key`. Run 2 (new process) → OK, but `payment_key` is NULL for all legacy rows (dedupe off for them). Also after migrating a legacy DB, all evidence has `agent_id` NULL (no re-link).
- Impact: only DBs from schema ≤ v3 with duplicate rows. Fixture is reconstructed (INFER).
- Fix: de-duplicate before the unique index; wrap in one transaction; re-link evidence by `author`.
- Evidence: EXEC x2 (cross-process).

**BUG-19 — Tests touch the real project DB; connections are never closed** · LOW
- Repro: after `pytest`, `data/agent_factory.db` and `data/raw/` exist in the project. `pytest -W error` fails.
- Fix: monkeypatch `DB`, `RAW`, `REPORTS` in that test. Close connections (context manager).
- Evidence: EXEC.

**BUG-20 — Dead config and stale versions** · LOW
- See section 17. Fix: remove `money`, `sources` or read them; set `__version__` from config; fix README and CHECKPOINT; drop `beautifulsoup4`.

**BUG-21 — Capability false positives** · LOW (see section 8).

**BUG-22 — Seed file creates non-agent "agents"** · LOW. Seed rows for a platform and a discussion get `agents` rows.

**BUG-23 — Reports embed raw external text** · LOW now, HIGH if reports feed a model. Hostile name and text inject Markdown headings (EXEC). Fix: escape or fence untrusted text; add a banner "UNTRUSTED DATA"; never feed reports to a model as instructions.

**BUG-24 — Allowlist ignores port; second redirect returned as success** · LOW. Fix: compare `netloc` or check `port in (None, 443)`; treat a final 3xx as error.

---

## 21. False Positive Analysis (bad item accepted)

Third-party claims by name or role (BUG-6); zero / `nothing` / no-amount claims as candidates (BUG-5); tx-shaped string in non-claims (BUG-8); conditional and question forms (BUG-16); capability from `code of conduct`, `by design` (BUG-21); non-agents from seed (BUG-22); secret solicitation passing the gate (BUG-1); edited posts and shared tx counted twice (BUG-12).

## 22. False Negative Analysis (good item dropped)

Genuine claims with `no/not/cannot/without` nearby (BUG-2); own claim next to `@mention`, quote line or friend's claim (BUG-7); amounts with `$`, `USD 10`, `DAI`, thousands separators (BUG-4); only the first amount per text; risk terms in plural or inflected form (BUG-9); `developer`, `engineer`, `analyst`, `translator` get no capability; empty Moltbook feed treated as failure; jobs lost at pagination cap (BUG-17).

## 23. Architecture Review

- Strength: strict stage chain, evidence-first, parameterised SQL, no secret handling, source isolation, honest `unverified` states.
- Weakness 1: **regex-over-whole-text design.** Claim, negation, third-party, intent and quote are five global regexes on one string. Every bug in 6, 7, 16 comes from this. Move to: split into clauses → find a first-person completed-payment clause → parse amount once → pass one `Claim` object to ledger, score, observation.
- Weakness 2: **no single source of truth** for money words, risk words and work words (BUG-14, 15, 20).
- Weakness 3: **score semantics.** Candidate = (earning ≥ 4 OR capability ≥ 3). A capability-only agent is a "candidate" for a system that wants earning agents. Risk is max-not-sum. NOTE.
- Weakness 4: migration code runs on each connect (BUG-3, 18).
- Weakness 5: no `verified` writer, no tx lookup. Planned. The ledger cannot yet tell a real payment from text.

## 24. Confirmed vs Unverified

**CONFIRMED BY EXECUTION:** everything marked EXEC above, including the 43 passing tests, CLI behaviour, all BUG-1…19, 24 reproductions, and the 15-row regression result.

**CONFIRMED BY CODE INSPECTION:** no dangerous call; parameterised SQL; no wallet code; dead config keys; `verified` never assigned; three classifiers.

**INFERRED:** prompt-injection risk of reports (BUG-23); reconstructed legacy schema (BUG-18); effect of BUG-3 after a verifier exists.

**UNVERIFIED / BLOCKED BY ENVIRONMENT:** live Moltbook and MoltJobs response shapes, auth, rate limits, real pagination; real post volume (BUG-11 and BUG-17 depend on whether real posts carry stable ids and how many jobs exist).

**NOT TESTED:** Windows run (`run_scout.bat`); concurrent runs; very large DB performance; Python 3.10–3.12; non-English text.

## 25. Recommended Fixes (priority order)

1. BUG-1 secret terms table + hard block.
2. BUG-2, 6, 7, 16, 15: replace global regexes with one clause-based `Claim` parser (first-person + completed verb + valid amount). Add tests with benign negation words, names, mentions, quotes, conditionals.
3. BUG-4, 5, 8: one amount parser; score from the parsed claim only.
4. BUG-3: move clean-up into a versioned migration; never delete.
5. BUG-11, 12, 13: author in hash; update by `external_id`; lower-case tx; normalise identity; unique `tx_hash` review flag.
6. BUG-9, 10, 14, 20: one vocabulary file with variants for risk, hype, work, category and money; validate all maps.
7. BUG-17, 18, 19, 23, 24.

## 26. Recommended v0.8 Scope

- Claim parser module with a table-driven test file (input → expected state, amount, subject). Include every case from section 6.
- Property tests: negation, third-party, idempotency, order, risk monotonicity.
- Vocabulary module; `category_set` and scoring read it.
- Secret-term hard block, separate from score.
- Migration module with `schema_version` guard.
- Test isolation (temp DB, temp reports).
- **Do not** start on-chain verification or Trust Wallet routing until items 1–5 pass. A verifier on top of this parser will verify the wrong claims.

## 27. Final Verdict

```text
BLOCKED — MUST FIX
```

Reason: BUG-1 (secret solicitation passes the gate), BUG-2 (genuine claims suppressed), BUG-4 (wrong amounts in the ledger), BUG-5, 6 and 8 (candidate selection accepts claims without a valid payment or from a third party). These are payment-state, identity and candidate-selection failures. They are not future features and not network limits.
