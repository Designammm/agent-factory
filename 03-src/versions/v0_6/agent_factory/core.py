from __future__ import annotations
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .sources import moltbook, moltjobs

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
DATA, RAW, REPORTS = ROOT / "data", ROOT / "data/raw", ROOT / "reports"
DB = DATA / "agent_factory.db"
for p in (DATA, RAW, REPORTS):
    p.mkdir(parents=True, exist_ok=True)
SCHEMA_VERSION = 6


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS agents(
        id INTEGER PRIMARY KEY, canonical_key TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
        profile_url TEXT, source TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS evidence(
        id INTEGER PRIMARY KEY, agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
        source TEXT NOT NULL, external_id TEXT, title TEXT, url TEXT, author TEXT, published TEXT,
        text TEXT NOT NULL, evidence_type TEXT NOT NULL, confidence TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0, fetched_at TEXT NOT NULL, content_hash TEXT NOT NULL,
        identity_confidence TEXT NOT NULL DEFAULT 'unknown',
        UNIQUE(source, content_hash))""")
    c.execute("""CREATE TABLE IF NOT EXISTS observations(
        id INTEGER PRIMARY KEY, agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        claim_type TEXT NOT NULL, value_json TEXT NOT NULL, confidence TEXT NOT NULL,
        created_at TEXT NOT NULL, UNIQUE(agent_id,evidence_id,claim_type))""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY, agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
        evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL, amount REAL, currency TEXT,
        network TEXT, tx_hash TEXT, verification TEXT NOT NULL, payment_state TEXT NOT NULL DEFAULT 'claim',
        observed_at TEXT, payment_key TEXT UNIQUE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS candidates(
        id INTEGER PRIMARY KEY, agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        earning_score INTEGER NOT NULL, capability_score INTEGER NOT NULL, risk_score INTEGER NOT NULL DEFAULT 0,
        confidence TEXT NOT NULL, categories TEXT NOT NULL, evidence_count INTEGER NOT NULL,
        payment_count INTEGER NOT NULL, verified_payment_count INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL, UNIQUE(agent_id))""")
    # V2/V3 -> V4 additive migration.
    cols = {r[1] for r in c.execute("PRAGMA table_info(evidence)")}
    if "agent_id" not in cols:
        c.execute("ALTER TABLE evidence ADD COLUMN agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL")
    if "identity_confidence" not in cols:
        c.execute("ALTER TABLE evidence ADD COLUMN identity_confidence TEXT NOT NULL DEFAULT 'unknown'")

    pcols = {r[1] for r in c.execute("PRAGMA table_info(payments)")}
    if "payment_state" not in pcols:
        c.execute("ALTER TABLE payments ADD COLUMN payment_state TEXT NOT NULL DEFAULT 'claim'")
    if "payment_key" not in pcols:
        c.execute("ALTER TABLE payments ADD COLUMN payment_key TEXT")
        rows = c.execute("SELECT id,agent_id,evidence_id,amount,currency,network,tx_hash FROM payments").fetchall()
        for row in rows:
            key = hash_text("|".join(str(row[k]) for k in ("agent_id","evidence_id","amount","currency","network","tx_hash")))
            c.execute("UPDATE payments SET payment_key=? WHERE id=?", (key, row["id"]))
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pay_key ON payments(payment_key)")

    ccols = {r[1] for r in c.execute("PRAGMA table_info(candidates)")}
    if "risk_score" not in ccols:
        c.execute("ALTER TABLE candidates ADD COLUMN risk_score INTEGER NOT NULL DEFAULT 0")
    if "verified_payment_count" not in ccols:
        c.execute("ALTER TABLE candidates ADD COLUMN verified_payment_count INTEGER NOT NULL DEFAULT 0")

    for row in c.execute("""SELECT p.id,e.text FROM payments p JOIN evidence e ON e.id=p.evidence_id
                            WHERE e.text IS NOT NULL""").fetchall():
        if is_negated_payment_claim(row["text"]):
            c.execute("DELETE FROM payments WHERE id=?", (row["id"],))

    for row in c.execute("SELECT id FROM agents WHERE canonical_key LIKE 'url:%'").fetchall():
        c.execute("UPDATE evidence SET agent_id=NULL, identity_confidence='url_only' WHERE agent_id=?", (row["id"],))
        c.execute("DELETE FROM agents WHERE id=?", (row["id"],))

    c.execute("CREATE INDEX IF NOT EXISTS idx_evidence_agent ON evidence(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evidence_hash ON evidence(content_hash)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_obs_agent ON observations(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pay_agent ON payments(agent_id)")
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    c.commit()
    return c


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def stable_job_key(j: dict) -> str:
    jid = str(j.get("id") or j.get("jobId") or "").strip()
    if jid:
        return jid
    return "sha256:" + hash_text(json.dumps(j, sort_keys=True, ensure_ascii=False))


def canonical_agent(author: str, url: str) -> tuple[str | None, str | None, str]:
    a = (author or "").strip()
    if a:
        return "author:" + a.casefold(), a, "author"
    return None, None, "url_only"


def upsert_agent(c, author: str, url: str, source: str) -> int:
    key, display, _ = canonical_agent(author, url)
    if not key or display == "unknown-agent":
        return 0
    row = c.execute("SELECT id FROM agents WHERE canonical_key=?", (key,)).fetchone()
    now = now_iso()
    if row:
        c.execute("UPDATE agents SET last_seen=?, profile_url=COALESCE(profile_url,?), source=COALESCE(source,?) WHERE id=?", (now,url,source,row["id"]))
        return row["id"]
    return c.execute("INSERT INTO agents(canonical_key,name,profile_url,source,first_seen,last_seen) VALUES(?,?,?,?,?,?)", (key,display,url,source,now,now)).lastrowid


def insert_evidence(c, *, source, title, url, author, published, text, evidence_type, confidence, verified, external_id="", agent_id=None, identity_confidence="unknown"):
    text = text.strip()
    if not text:
        return 0, False
    content_hash = hash_text("\n".join([source, external_id, url, title, text]))
    row = c.execute("SELECT id FROM evidence WHERE source=? AND content_hash=?", (source, content_hash)).fetchone()
    if row:
        c.execute(
            "UPDATE evidence SET agent_id=COALESCE(agent_id,?), "
            "identity_confidence=CASE WHEN identity_confidence='unknown' THEN ? ELSE identity_confidence END WHERE id=?",
            (agent_id, identity_confidence, row["id"])
        )
        return row["id"], False
    eid = c.execute(
        """INSERT INTO evidence(agent_id,source,external_id,title,url,author,published,text,evidence_type,confidence,verified,fetched_at,content_hash,identity_confidence)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (agent_id,source,external_id,title,url,author,published,text[:100000],evidence_type,confidence,int(verified),now_iso(),content_hash,identity_confidence)
    ).lastrowid
    return eid, True


def ingest_seed_findings(c) -> int:
    path = DATA / "seed_findings.json"
    if not path.exists(): return 0
    count = 0
    for item in json.loads(path.read_text(encoding="utf-8")):
        source = str(item.get("source","seed")); author = str(item.get("agent","")); url = str(item.get("url",""))
        text = json.dumps(item, ensure_ascii=False)
        aid = upsert_agent(c, author, url, source) if author else None
        eid, created = insert_evidence(c, source=source,title=author or str(item.get("title","Seed finding")),url=url,author=author,published="",text=text,evidence_type="seed_research",confidence=str(item.get("confidence","low")),verified=False,external_id=str(item.get("id","")),agent_id=aid or None)
        if created: count += 1
        if aid and eid:
            claim = classify_claim(text)
            c.execute("INSERT OR IGNORE INTO observations(agent_id,evidence_id,claim_type,value_json,confidence,created_at) VALUES(?,?,?,?,?,?)", (aid,eid,claim,json.dumps({"text":text},ensure_ascii=False),str(item.get("confidence","low")),now_iso()))
            extract_and_store_payments(c, aid, eid, text)
    return count


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.casefold()))


_NEGATION = r"(?:not|no|without|never|did\s+not|didn['’]t|does\s+not|doesn['’]t|do\s+not|don['’]t|has\s+not|hasn['’]t|have\s+not|haven['’]t|was\s+not|wasn['’]t|were\s+not|weren['’]t|is\s+not|isn['’]t|are\s+not|aren['’]t|cannot|can['’]t)"
_PAYMENT_TARGET = r"(?:paid|pay|payment|payout|payouts|earn|earned|earns|earning|earnings|income|revenue|received|receive|settled|settle|released|release|tx|transaction|hash|proof|usdc|usd|near|bounty|escrow)"


def is_negated_payment_claim(text: str) -> bool:
    t = text.casefold()
    return bool(
        re.search(rf"\b{_NEGATION}\b.{{0,45}}\b{_PAYMENT_TARGET}\b", t)
        or re.search(rf"\b{_PAYMENT_TARGET}\b.{{0,25}}\b{_NEGATION}\b", t)
    )


def classify_claim(text: str) -> str:
    if is_negated_payment_claim(text):
        return "negated_payment_claim"
    if re.search(r"\b(?:paid|payout|payment|earn(?:ed|s|ing)?|revenue|income|settled|received|released)\b", text.casefold()):
        return "payment_claim"
    return "public_capability_claim"


def _money_amount_re() -> str:
    return r"\b\d+(?:\.\d+)?\s*(?:usdc|usd|near)\b"


def extract_payment(text: str) -> tuple[float | None, str | None, str | None]:
    m = re.search(_money_amount_re(), text, re.I)
    if not m:
        return None, None, None
    amount_match = re.search(r"\d+(?:\.\d+)?", m.group(0))
    amount = float(amount_match.group(0)) if amount_match else None
    cm = re.search(r"(?:USDC|USD|NEAR)", m.group(0), re.I)
    currency = cm.group(0).upper() if cm else None
    network = "Base" if re.search(r"\bBase\b", text, re.I) else None
    return amount, currency, network


def extract_tx_hash(text: str) -> str | None:
    m = re.search(r"\b0x[a-fA-F0-9]{64}\b", text)
    return m.group(0) if m else None


def _third_party_or_quoted_claim(text: str) -> bool:
    t = text.casefold()
    if re.search(r"(?m)^\s*>.*\b(?:earned|received|made|was paid|got paid)\b", t):
        return True
    return bool(re.search(
        r"\b(?:my friend|a friend|another agent|the agent|that agent|someone|somebody|he|she|they|them|the user|users|clients?)\b.{0,35}\b(?:earned|received|made|settled|released|got paid|was paid)\b",
        t,
    ))


def _completed_payment_claim(text: str) -> bool:
    t = text.casefold()
    if is_negated_payment_claim(t) or _third_party_or_quoted_claim(t):
        return False
    # Completed/reported receipt verbs. Intent verbs such as "want to earn"
    # and generic job descriptions such as "jobs can pay" are excluded.
    if re.search(r"\b(?:earned|received|collected|made|settled|released)\b", t):
        if re.search(r"\b(?:want(?:s)?\s+to|hope(?:s)?\s+to|plan(?:s)?\s+to|trying\s+to|aim(?:s)?\s+to|can|could|may|might|should|would|will|target(?:s)?|goal)\b.{0,30}\b(?:earn|earned|receive|received|make|made|settle|settled|release|released)\b", t):
            return False
        return True
    if re.search(r"\b(?:got|gotten|was|were|has been|have been)\s+(?:paid|a payout|payment)\b", t):
        return True
    if re.search(r"\b(?:payout|payment)\s+(?:was|is|has been)\s+(?:received|released|settled)\b", t):
        return True
    return False


def payment_state(text: str, tx_hash: str | None) -> str:
    if is_negated_payment_claim(text):
        return "negated_claim"
    if tx_hash and _completed_payment_claim(text):
        return "evidence_pending_verification"
    if _completed_payment_claim(text):
        return "claim"
    return "non_claim"


def extract_and_store_payments(c, agent_id, evidence_id, text):
    amount, currency, network = extract_payment(text)
    tx = extract_tx_hash(text)
    if amount is None:
        return 0
    state = payment_state(text, tx)
    if state in {"negated_claim", "non_claim"}:
        return 0
    verification = "tx_present_unverified" if tx else "unverified"
    key = hash_text("|".join(str(x) for x in (agent_id, evidence_id, amount, currency, network, tx, state)))
    c.execute(
        """INSERT OR IGNORE INTO payments
           (agent_id,evidence_id,amount,currency,network,tx_hash,verification,payment_state,observed_at,payment_key)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (agent_id,evidence_id,amount,currency,network,tx,verification,state,now_iso(),key)
    )
    return 1


def _contains_work_term(t: str, term: str) -> bool:
    variants = CFG.get("work_variants", {})
    values = variants.get(term, [term])
    return any(re.search(rf"\b{re.escape(v)}\b", t) for v in values)


def _contains_risk_term(t: str, term: str) -> bool:
    variants = CFG.get("risk_variants", {})
    values = variants.get(term, [term])
    return any(re.search(rf"\b{re.escape(v)}\b", t) for v in values)


def score_evidence(text: str) -> tuple[int, int, int, list[str]]:
    t = text.casefold()
    w = tokens(t)
    earning = capability = risk = 0
    signals = []
    negated = is_negated_payment_claim(t)
    completed_claim = _completed_payment_claim(t)

    positive_money = re.search(r"\b(?:paid|payout|payouts|payment|payments|earned|earns|earning|earnings|revenue|income|settled|received|released|escrow|bounty)\b", t)
    explicit_amount = re.search(_money_amount_re(), t, re.I)
    currency_context = bool(re.search(r"\b(?:usdc|usd)\b", t)) or bool(
        re.search(r"\bnear\b", t) and re.search(r"\b(?:protocol|chain|wallet|payout|payment|earned|earning|currency|crypto)\b", t)
    )

    if not negated and (positive_money or currency_context):
        earning += 1; signals.append("money-language")
    if explicit_amount and not negated:
        # An amount alone is weak informational evidence. It becomes a strong
        # earning signal only when the text contains a completed receipt claim.
        if completed_claim:
            earning += 3; signals.append("explicit-amount")
        else:
            earning += 1; signals.append("amount-mentioned")
    if completed_claim:
        earning += 3; signals.append("payment-claim")
    if not negated and re.search(r"\b(?:tx|transaction|txid|hash)\b.{0,60}\b(?:usdc|usd|near|base|0x[a-f0-9]{64})\b", t):
        earning += 2; signals.append("transaction-context")

    work_terms = [x for x in CFG["work"] if x not in {"api", "automation"}]
    if any(_contains_work_term(t, term) for term in work_terms):
        capability += 2; signals.append("work-capability")
    if any(_contains_work_term(t, term) for term in CFG["automation"] if term != "api"):
        capability += 2; signals.append("automation")
    if re.search(r"\bapi(?:\s+integration)?\b", t):
        capability += 1; signals.append("api-capability")
    if "github.com" in t or "open source" in t or "opensource" in t:
        capability += 2; signals.append("public-code")

    for phrase in CFG["risk"]:
        if phrase in CFG.get("risk_variants", {}):
            matched = _contains_risk_term(t, phrase)
        else:
            matched = bool(re.search(rf"\b{re.escape(phrase)}\b", t))
        if matched:
            risk += 2
    if re.search(r"\b(?:private key|seed phrase|secret key|wallet credentials?|login credentials?|api key)\b", t):
        risk += 5

    hype_terms = CFG.get("risk_hype", [])
    hype_count = sum(1 for x in hype_terms if re.search(rf"\b{re.escape(x)}\b", t))
    money_count = len(re.findall(r"\b(?:usdc|usd|near|paid|payout|payment|payments|earned|earning|income|revenue|bounty|escrow|settled|released)\b", t))
    if hype_count:
        risk += min(6, 2 * hype_count)
    # A completed earnings claim combined with hype is materially riskier than
    # either signal alone. Keep the ordinary claim score intact, but make the
    # combination cross the default candidate gate for strong hype.
    if completed_claim and hype_count:
        risk += 3
    if len(w) <= 24 and money_count >= 5:
        risk += 3
    if len(w) and money_count >= 6 and money_count / len(w) >= 0.20:
        risk += 3

    return min(20, earning), min(20, capability), min(20, risk), signals


def category_set(text: str) -> list[str]:
    t = text.casefold()
    groups = {
        "research": [r"\bresearch(?:er|ing|ed)?\b", r"\bmarket research\b", r"\breport(?:s|ing|ed)?\b"],
        "data": [r"\bdata\b", r"\bdatasets?\b", r"\bdata extraction\b", r"\bscrap(?:e|ing|er|ers)\b", r"\bclassification\b", r"\bcsv\b"],
        "software": [r"\bpython\b", r"\bjavascript\b", r"\btypescript\b", r"\bbug(?:s)?\b", r"\bapi(?: integration)?\b", r"\bcod(?:e|ing|er|ers)\b", r"\bsoftware\b"],
        "content": [r"\bcontent\b", r"\barticles?\b", r"\bcopywriting\b"],
        "qa": [r"\bqa\b", r"\btest(?:ing|er|ers|ed)?\b", r"\btest coverage\b", r"\bbug reproduction\b"],
        "lead_gen": [r"\blead[- ]?gen\b", r"\bleads\b", r"\bprospecting\b"]
    }
    found = [k for k, pats in groups.items() if any(re.search(p, t) for p in pats)]
    return found or ["unknown"]


def confidence_rank(c): return {"low":1,"medium":2,"high":3}.get(c,1)


def candidate_rows(c):
    rows = c.execute("""SELECT a.id,a.name,a.profile_url,a.source,
        COUNT(DISTINCT e.id) evidence_count,
        COUNT(DISTINCT CASE WHEN p.payment_state!='negated_claim' THEN p.id END) payment_count,
        COUNT(DISTINCT CASE WHEN p.verification='verified' AND p.payment_state!='negated_claim' THEN p.id END) verified_payment_count,
        GROUP_CONCAT(DISTINCT e.confidence) confidences
        FROM agents a LEFT JOIN evidence e ON e.agent_id=a.id LEFT JOIN payments p ON p.agent_id=a.id
        GROUP BY a.id ORDER BY a.last_seen DESC""").fetchall()
    out=[]
    thresholds=CFG["thresholds"]
    risk_gate=bool(thresholds.get("risk_gate_enabled", True))
    max_risk=int(thresholds.get("candidate_max_risk", 6))
    for r in rows:
        evidence_rows = c.execute("SELECT text FROM evidence WHERE agent_id=? ORDER BY id", (r["id"],)).fetchall()
        scores = [score_evidence(x["text"] or "") for x in evidence_rows]
        earning = max((x[0] for x in scores), default=0)
        capability = min(20, sum(x[1] for x in scores))
        risk = max((x[2] for x in scores), default=0)
        signals=[]
        for _,_,_,sig in scores:
            for item in sig:
                if item not in signals:
                    signals.append(item)
        verified_count=r["verified_payment_count"] or 0
        if verified_count:
            earning += min(10,verified_count*5); signals.append("verified-payment")
        if risk_gate and risk > max_risk:
            continue
        if earning < thresholds["earning_min"] and capability < thresholds["capability_min"]:
            continue
        confs=[x for x in (r["confidences"] or "").split(",") if x]
        confidence=min(confs,key=confidence_rank) if confs else "low"
        # Categories are derived from the union of evidence, not a concatenated
        # scoring blob, so a negated claim cannot suppress an unrelated positive claim.
        cats=[]
        for x in evidence_rows:
            for cat in category_set(x["text"] or ""):
                if cat not in cats and cat != "unknown": cats.append(cat)
        out.append({"agent_id":r["id"],"name":r["name"],"url":r["profile_url"] or "",
                    "earning_score":earning,"capability_score":capability,"risk_score":risk,
                    "confidence":confidence,"categories":cats or ["unknown"],
                    "evidence_count":r["evidence_count"],"payment_count":r["payment_count"],
                    "verified_payment_count":verified_count,"signals":signals})
    return sorted(out,key=lambda x:(x["earning_score"],x["capability_score"],-x["risk_score"]),reverse=True)


def rebuild_candidates(c):
    xs=candidate_rows(c); c.execute("DELETE FROM candidates")
    for x in xs[:100]:
        c.execute("INSERT INTO candidates(agent_id,earning_score,capability_score,risk_score,confidence,categories,evidence_count,payment_count,verified_payment_count,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(x["agent_id"],x["earning_score"],x["capability_score"],x["risk_score"],x["confidence"],",".join(x["categories"]),x["evidence_count"],x["payment_count"],x["verified_payment_count"],now_iso()))
    c.commit(); return xs


def blueprint(c,x):
    safe=hashlib.sha1(f"{x['agent_id']}:{x['name']}".encode()).hexdigest()[:10]
    slug=re.sub(r"[^a-z0-9]+","-",x["name"].casefold()).strip("-")[:50] or "agent"
    p=REPORTS/f"{slug}-{safe}.md"
    evidence=c.execute("SELECT source,title,url,confidence,verified,evidence_type,text FROM evidence WHERE agent_id=? ORDER BY fetched_at DESC LIMIT 10",(x["agent_id"],)).fetchall()
    lines=[f"# Agent Intelligence: {x['name']}","",f"Earning score: **{x['earning_score']}**",f"Capability score: **{x['capability_score']}**",f"Risk score: **{x['risk_score']}**",f"Confidence: **{x['confidence']}**",f"Categories: **{', '.join(x['categories'])}**",f"Payments extracted: **{x['payment_count']}** | Verified: **{x['verified_payment_count']}**","","## Interpretation","Scores are discovery signals. A payment claim is not a verified payment. OPEN jobs are demand evidence, not agent earnings.","","## Evidence"]
    for e in evidence: lines += [f"### {e['source']} — {e['title']}",f"Type: {e['evidence_type']} | Confidence: {e['confidence']} | Verified flag: {bool(e['verified'])}",f"URL: {e['url']}","",e["text"][:2500],""]
    lines += ["## Rebuild hypotheses","1. Identify customer-facing output.","2. Identify tools/data/APIs and constraints.","3. Rebuild independently; respect licenses and terms.","4. Define deterministic acceptance tests.","5. Test locally before paid execution.","6. Keep bidding, execution and payment actions behind explicit controls.","7. Measure revenue, tool cost, rejection rate and time per job."]
    p.write_text("\n".join(lines),encoding="utf-8"); return str(p)


def init_db():
    c=conn(); n=ingest_seed_findings(c); c.commit(); print(f"Database ready: {DB}"); print(f"Seed findings imported/updated: {n}")


def collect():
    c=conn(); imported=ingest_seed_findings(c); mb=0; mj=0
    try:
        items=moltbook.collect(); (RAW/"moltbook_feed.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
        for item in items:
            aid=upsert_agent(c,item["author"],item["url"],"moltbook") if item["author"] else None
            identity="author" if item["author"] else "url_only"
            eid,created=insert_evidence(c,source="moltbook",external_id=item["external_id"],title=item["title"],url=item["url"],author=item["author"],published=item["published"],text=item["text"],evidence_type="public_post",confidence="low",verified=False,agent_id=aid or None,identity_confidence=identity)
            if created: mb+=1
            if aid and eid:
                c.execute("INSERT OR IGNORE INTO observations(agent_id,evidence_id,claim_type,value_json,confidence,created_at) VALUES(?,?,?,?,?,?)",(aid,eid,classify_claim(item["text"]),json.dumps({"signals":score_evidence(item["text"])[3]},ensure_ascii=False),"low",now_iso()))
                extract_and_store_payments(c,aid,eid,item["text"])
    except Exception as ex: print("[WARN] Moltbook:",ex)
    try:
        jobs=moltjobs.pages(); (RAW/"moltjobs_open_jobs.json").write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding="utf-8")
        for j in jobs:
            title=str(j.get("title") or j.get("name") or "MoltJobs job")
            jid=stable_job_key(j); url=str(j.get("url") or j.get("webUrl") or f"https://moltjobs.io/jobs/{jid.replace('sha256:','')}")
            text=moltjobs.job_text(j)
            eid,created=insert_evidence(c,source="moltjobs",external_id=jid,title=title,url=url,author="",published=str(j.get("createdAt", "")),text=text,evidence_type="open_job",confidence="high",verified=False,agent_id=None,identity_confidence="unknown")
            if created: mj+=1
    except Exception as ex: print("[WARN] MoltJobs:",ex)
    c.commit(); return imported+mb,mj


def scout():
    print("== AGENT FACTORY v0.5.0 =="); imported,jobs=collect(); c=conn(); xs=rebuild_candidates(c)
    for x in xs[:100]: blueprint(c,x)
    print(f"New/seed evidence imported: {imported}"); print(f"New MoltJobs jobs: {jobs}"); print("Evidence:",c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]); print("Agents:",c.execute("SELECT COUNT(*) FROM agents").fetchone()[0]); print("Candidates:",len(xs))
    for x in xs[:10]: print(f"{x['earning_score']:>3} earn | {x['capability_score']:>3} cap | {x['risk_score']:>3} risk | {x['confidence']:<6} | {x['name']:<30} | {','.join(x['categories'])}")


def verify_sources():
    print("== SOURCE VERIFICATION ==")
    for label,fn in [("Moltbook API feed",moltbook.collect),("MoltJobs OPEN",moltjobs.pages)]:
        try: print(f"[OK] {label}: {len(fn())} records")
        except Exception as ex: print(f"[FAIL] {label}: {type(ex).__name__}: {ex}")


def report():
    c=conn(); rows=c.execute("SELECT a.name,a.profile_url,c.earning_score,c.capability_score,c.risk_score,c.confidence,c.categories,c.evidence_count,c.payment_count,c.verified_payment_count FROM candidates c JOIN agents a ON a.id=c.agent_id ORDER BY c.earning_score DESC,c.capability_score DESC LIMIT 25").fetchall()
    if not rows: print("No candidates. Run: python -m agent_factory scout"); return
    print("== AGENT INTELLIGENCE ==")
    for r in rows: print(f"\n[{r['earning_score']} earn / {r['capability_score']} cap / {r['risk_score']} risk] {r['name']} ({r['confidence']})\nCategories: {r['categories']} | Evidence: {r['evidence_count']} | Payments: {r['payment_count']} | Verified: {r['verified_payment_count']}\n{r['profile_url'] or ''}")
