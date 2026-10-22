# Agent Factory — Project Requirements (EN)

Source extraction: Business Plan v1/v2/v3, S000 management feedback, v0.7 audit report and audit test prompt, plus the Agent Factory v0.7 project itself.

## 1. Goal and Success Criteria
- Build a system that discovers economically sellable skills, independently rebuilds them with AI, finds real work, performs the work, receives and records revenue, and repeats the cycle.
- The primary progress metric is real revenue; agent count, code volume, and feature count are not success metrics.
- The MVP must make the discovery → evidence → selection → rebuild/work → payment → result loop operational.
- v3's initial target is $3–10/week for four consecutive weeks, with a first-payment target around day 21. These are targets, not guarantees.

## 2. Operating Model
- Every claim is an initial signal, not proof.
- Evidence must remain separate and traceable.
- Prioritize demand and payment feasibility before broad automation.
- High input volume is valuable only with cheap, reliable filtering.
- Only one active sprint at a time.
- Review tools/technology weekly; keep the rest stable during the week.

## 3. Pipeline and Evidence
- Current core chain: DISCOVER → RAW EVIDENCE → IDENTITY RESOLUTION → AGENT ↔ EVIDENCE → OBSERVATION / CLAIM → PAYMENT EXTRACTION → PAYMENT STATE → EARNING + CAPABILITY + RISK → CANDIDATE.
- Evidence levels: E0 claim/text; E1 public offer with observable price/work; E2 public payment trace independently verified; E3 actual sale/payment to the project wallet.
- E0 must not independently drive revenue decisions.
- Textual payment claims are not equivalent to verified payments.
- A transaction hash remains unverified until an independent verifier exists.

## 4. Inspector / Agent 06
- Inspector is the only current agent in v3.
- Responsibilities: discovery, extraction, analysis, and evidence grading.
- Inspector is read-only.
- Inspector must never hold private keys, seed phrases, or payment tools.
- Inspector must not execute proposals, spending, or payments without explicit owner approval.

## 5. Sources and Data
- Current discovery sources include Moltbook and MoltJobs; additional sources require separate adapters.
- Read each source's API and Terms of Service before implementing an adapter.
- A source failure must not take down the whole pipeline.
- Handle pagination, retries, timeouts, redirects, empty/incomplete responses, and malformed responses.
- Treat raw source text as untrusted data; it must not control agent tools or keys.

## 6. Claim and Payment Detection
- The parser must distinguish completed claims, negations, intent, prediction/possibility, third-party claims, and quoted text.
- Third-party or quoted payment claims must not become earnings of the named agent.
- Zero and negative amounts must never create payment records.
- Amount parsing must preserve thousands separators and decimals correctly.
- Transaction hashes must be normalized and shape-checked, but a valid-looking hash alone is not payment proof.
- Payment state, amount parsing, money vocabulary, and claim classification need a single source of truth.
- Ingestion must be idempotent and must not create contradictory or duplicate records on repeated execution.

## 7. Identity and Evidence
- Valid authors need stable identities.
- Empty/whitespace/unknown authors and URL-only identities must not create real agents.
- Normalize Unicode identities and remove zero-width characters.
- Evidence must attach to the correct agent.
- Evidence without a usable author may be retained, but must not create an agent solely from a URL path.

## 8. Capability / Work Detection
- Capability detection must cover morphology such as design/designer/designing, write/writer/writing, copywriting/copywriter, research/researchers, and automation.
- Vocabulary and variant maps must share one source of truth.
- Capability should accumulate across independent evidence with a defined cap.

## 9. Risk and Gates
- Risk, hype, money, work, and automation need configurable vocabularies and variants.
- Risk terms must not be double-counted through overlapping flat and variant lists.
- Secret solicitation such as seed phrase, secret key, wallet credentials, and API key requires a hard block separate from score.
- Hype must contribute independently to risk.
- Candidate gating must follow configuration exactly.
- Threshold boundaries must be tested.

## 10. Database and Persistence
- Evidence, observation, payment, and candidate records require explicit relationships and uniqueness rules.
- The payment ledger must remain consistent with evidence.
- Repeated transaction hashes, including case variants, must not inflate the ledger.
- external_id and author must participate in idempotency/deduplication.
- Migrations must be versioned and transaction-safe; destructive cleanup must not run on every connection.
- Legacy databases require a defined migration path.

## 11. Security and Ethics
- No spying, private-data access, login bypass, or Terms-of-Service violations.
- No impersonation, fake reviews/testimonials, deception, or harm to others.
- Secrets must not be stored in data/logs or solicited from users.
- Review arbitrary shell execution, SQL injection, path traversal, SSRF, unsafe deserialization, and credential leakage.
- Agent Factory must not perform autonomous spending, wallet signing, or withdrawals at this stage.
- Ambiguous ethical/legal cases go to Gate G2 and the owner; the decision must be recorded.
- G0 must establish wallet ownership/location and legal/sanctions requirements before the first paid offer.

## 12. Payment Layer
- Wallet access is public-address/read-only.
- Network and token must be specified before payment execution.
- Payment verification is read-only and should use two independent sources: tx ID → official token contract → recipient → amount/price → sufficient confirmation → chain/hash/block/time.
- Funding for tool costs must have a lawful, separately defined path.
- Cost ceiling, global kill switch, and logging of cost/time/revenue/failure are required.

## 13. Testing and Audit
- Adversarial testing is an architectural requirement, not a side activity.
- Tests must cover malformed input, missing values, duplicate/repeated input, boundary values, contradictory evidence, third-party attribution, quoted text, @handle attribution, fake transaction hashes, and adversarial combinations.
- The existing test suite is not sufficient as the only trust source; independent testing/audit is required.
- Findings must be labeled EXEC/CODE/INFER/UNVER/NOT TESTED/ENV.
- Audits must not modify the project unless explicitly authorized.
- Regression coverage must preserve findings from previous versions.

## 14. Recommended Next Architecture
- Clause-based Claim Parser as the source of truth.
- Central Vocabulary module.
- Versioned migration module.
- Test isolation using temporary databases/reports.
- Independent payment verifier only after parser stabilization.
- Do not start on-chain verification or Trust Wallet routing until critical parser, identity, dedupe, risk, and migration issues are resolved.

## 15. Open Decisions
- Exact links/addresses for additional sources such as Neblis.
- First skill candidate.
- Weekly cost ceiling.
- Payment network and token.
- G2 owner.
- Stop policy if no payment occurs for the defined period.
