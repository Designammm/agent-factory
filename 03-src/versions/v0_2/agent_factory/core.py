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

SCHEMA_VERSION = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS agents(
        id INTEGER PRIMARY KEY,
        canonical_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        profile_url TEXT,
        source TEXT,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS evidence(
        id INTEGER PRIMARY KEY,
        source TEXT NOT NULL,
        external_id TEXT,
        title TEXT,
        url TEXT,
        author TEXT,
        published TEXT,
        text TEXT NOT NULL,
        evidence_type TEXT NOT NULL,
        confidence TEXT NOT NULL,
        verified INTEGER NOT NULL DEFAULT 0,
        fetched_at TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        UNIQUE(source, content_hash)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS observations(
        id INTEGER PRIMARY KEY,
        agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
        claim_type TEXT NOT NULL,
        value_json TEXT NOT NULL,
        confidence TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(agent_id, evidence_id, claim_type)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY,
        agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
        evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL,
        amount REAL,
        currency TEXT,
        network TEXT,
        tx_hash TEXT,
        verification TEXT NOT NULL,
        observed_at TEXT,
        UNIQUE(tx_hash)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS candidates(
        id INTEGER PRIMARY KEY,
        agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
        earning_score INTEGER NOT NULL,
        capability_score INTEGER NOT NULL,
        confidence TEXT NOT NULL,
        categories TEXT NOT NULL,
        evidence_count INTEGER NOT NULL,
        payment_count INTEGER NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(agent_id)
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evidence_fetched ON evidence(fetched_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evidence_author ON evidence(author)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_obs_agent ON observations(agent_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pay_agent ON payments(agent_id)")
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    c.commit()
    return c


def init_db() -> None:
    c = conn()
    seed_count = ingest_seed_findings(c)
    c.commit()
    print(f"Database ready: {DB}")
    print(f"Seed findings imported/updated: {seed_count}")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def stable_job_key(j: dict) -> str:
    jid = str(j.get("id") or j.get("jobId") or "").strip()
    if jid:
        return jid
    return "sha256:" + hash_text(json.dumps(j, sort_keys=True, ensure_ascii=False))


def canonical_agent(author: str, url: str) -> tuple[str, str]:
    a = (author or "").strip()
    if a:
        return "author:" + a.casefold(), a
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path
    key = f"url:{host}{path}"
    return key, (path.rstrip("/").split("/")[-1] or host or "unknown-agent")


def upsert_agent(c: sqlite3.Connection, author: str, url: str, source: str) -> int:
    key, display = canonical_agent(author, url)
    row = c.execute("SELECT id FROM agents WHERE canonical_key=?", (key,)).fetchone()
    now = now_iso()
    if row:
        c.execute("UPDATE agents SET last_seen=?, profile_url=COALESCE(profile_url,?), source=COALESCE(source,?) WHERE id=?", (now, url, source, row["id"]))
        return row["id"]
    cur = c.execute("INSERT INTO agents(canonical_key,name,profile_url,source,first_seen,last_seen) VALUES(?,?,?,?,?,?)", (key, display, url, source, now, now))
    return cur.lastrowid


def insert_evidence(c: sqlite3.Connection, *, source: str, title: str, url: str, author: str, published: str, text: str, evidence_type: str, confidence: str, verified: bool, external_id: str = "") -> tuple[int, bool]:
    text = text.strip()
    if not text:
        return 0, False
    content_hash = hash_text("\n".join([source, external_id, url, title, text]))
    row = c.execute("SELECT id FROM evidence WHERE source=? AND content_hash=?", (source, content_hash)).fetchone()
    if row:
        return row["id"], False
    cur = c.execute("""INSERT INTO evidence(source,external_id,title,url,author,published,text,evidence_type,confidence,verified,fetched_at,content_hash)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (source, external_id, title, url, author, published, text[:100000], evidence_type, confidence, int(verified), now_iso(), content_hash))
    return cur.lastrowid, True


def ingest_seed_findings(c: sqlite3.Connection) -> int:
    path = DATA / "seed_findings.json"
    if not path.exists():
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for item in items:
        source = str(item.get("source", "seed"))
        title = str(item.get("agent", item.get("title", "Seed finding")))
        url = str(item.get("url", ""))
        author = str(item.get("agent", ""))
        text = json.dumps(item, ensure_ascii=False)
        eid, created = insert_evidence(c, source=source, title=title, url=url, author=author, published="", text=text, evidence_type="seed_research", confidence=str(item.get("confidence", "low")), verified=False, external_id=str(item.get("id", "")))
        if created:
            count += 1
        if author:
            aid = upsert_agent(c, author, url, source)
            if eid:
                claim_type = "payment_claim" if re.search(r"\b(?:paid|payment|earned|settled|payout|usdc)\b", text, re.I) else "public_capability_claim"
                c.execute("""INSERT OR IGNORE INTO observations(agent_id,evidence_id,claim_type,value_json,confidence,created_at)
                    VALUES(?,?,?,?,?,?)""", (aid, eid, claim_type, text, str(item.get("confidence", "low")), now_iso()))
    return count


def extract_payment(text: str) -> tuple[float | None, str | None, str | None]:
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(USDC|USD|NEAR)\b", text, re.I)
    if not m:
        return None, None, None
    amount = float(m.group(1))
    currency = m.group(2).upper()
    network = "Base" if re.search(r"\bBase\b", text, re.I) else None
    return amount, currency, network


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.casefold()))


def score_evidence(text: str) -> tuple[int, int, list[str], list[str]]:
    t = text.casefold()
    w = words(t)
    earning = 0
    capability = 0
    earning_ev: list[str] = []
    capability_ev: list[str] = []

    money = set(CFG["money"])
    work = CFG["work"]
    automation = set(CFG["automation"])
    if w & money:
        earning += 2
        earning_ev.append("money-language")
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:usdc|usd|near)\b", t):
        earning += 4
        earning_ev.append("explicit-amount")
    if re.search(r"\b(?:paid|payout|payment|earned|revenue|income)\b.{0,80}\b(?:received|settled|released|transaction|tx|wallet)\b", t):
        earning += 4
        earning_ev.append("payment-context")
    if re.search(r"\b(?:tx|transaction|txid|hash)\b", t) and re.search(r"\b(?:usdc|usd|near|base)\b", t):
        earning += 5
        earning_ev.append("possible-onchain-reference")

    if any(term in t for term in work):
        capability += 2
        capability_ev.append("work-capability")
    if w & automation:
        capability += 2
        capability_ev.append("automation")
    if "github.com" in t or "open source" in t or "opensource" in t:
        capability += 2
        capability_ev.append("public-code")

    return earning, capability, earning_ev, capability_ev


def category_set(text: str) -> list[str]:
    t = text.casefold()
    found = []
    groups = {
        "research": [r"\bresearch\b", r"\bmarket research\b", r"\breport\b"],
        "data": [r"\bdata extraction\b", r"\bscraping\b", r"\bclassification\b", r"\bcsv\b"],
        "software": [r"\bpython\b", r"\bjavascript\b", r"\btypescript\b", r"\bbug\b", r"\bapi integration\b", r"\bcoding\b"],
        "content": [r"\bcontent\b", r"\barticle\b", r"\bcopywriting\b"],
        "qa": [r"\bqa\b", r"\btesting\b", r"\btest coverage\b", r"\bbug reproduction\b"],
        "lead_gen": [r"\blead gen\b", r"\bleads\b", r"\bprospecting\b"],
    }
    for k, patterns in groups.items():
        if any(re.search(p, t) for p in patterns):
            found.append(k)
    return found or ["unknown"]


def confidence_rank(c: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(c, 1)


def candidate_rows(c: sqlite3.Connection) -> list[dict]:
    rows = c.execute("""SELECT a.id,a.name,a.profile_url,a.source,
        COUNT(DISTINCT e.id) evidence_count,
        COUNT(DISTINCT p.id) payment_count,
        GROUP_CONCAT(DISTINCT e.confidence) confidences,
        GROUP_CONCAT(DISTINCT e.text) all_text
        FROM agents a
        LEFT JOIN evidence e ON e.author=a.name OR e.author LIKE a.name
        LEFT JOIN payments p ON p.agent_id=a.id
        GROUP BY a.id ORDER BY a.last_seen DESC""").fetchall()
    out = []
    for r in rows:
        text = r["all_text"] or ""
        earning, capability, ev1, ev2 = score_evidence(text)
        if earning < CFG["thresholds"]["earning_min"] and capability < CFG["thresholds"]["capability_min"]:
            continue
        confs = [x for x in (r["confidences"] or "").split(",") if x]
        confidence = min(confs, key=confidence_rank) if confs else "low"
        out.append({
            "agent_id": r["id"], "name": r["name"], "url": r["profile_url"] or "", "earning_score": earning,
            "capability_score": capability, "confidence": confidence,
            "categories": category_set(text), "evidence_count": r["evidence_count"], "payment_count": r["payment_count"],
            "signals": ev1 + ev2,
        })
    return sorted(out, key=lambda x: (x["earning_score"], x["capability_score"], x["payment_count"]), reverse=True)


def rebuild_candidates(c: sqlite3.Connection) -> list[dict]:
    xs = candidate_rows(c)
    c.execute("DELETE FROM candidates")
    for x in xs[:100]:
        c.execute("""INSERT INTO candidates(agent_id,earning_score,capability_score,confidence,categories,evidence_count,payment_count,updated_at)
            VALUES(?,?,?,?,?,?,?,?)""", (x["agent_id"], x["earning_score"], x["capability_score"], x["confidence"], ",".join(x["categories"]), x["evidence_count"], x["payment_count"], now_iso()))
    c.commit()
    return xs


def blueprint(c: sqlite3.Connection, x: dict) -> str:
    safe = hashlib.sha1(f"{x['agent_id']}:{x['name']}".encode()).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", x["name"].casefold()).strip("-")[:50] or "agent"
    p = REPORTS / f"{slug}-{safe}.md"
    evidence = c.execute("SELECT e.source,e.title,e.url,e.confidence,e.verified,e.text FROM evidence e JOIN agents a ON (e.author=a.name OR e.author LIKE a.name) WHERE a.id=? ORDER BY e.fetched_at DESC LIMIT 10", (x["agent_id"],)).fetchall()
    lines = [f"# Agent Intelligence: {x['name']}", "", f"Earning evidence score: **{x['earning_score']}**", f"Capability score: **{x['capability_score']}**", f"Confidence: **{x['confidence']}**", f"Categories: **{', '.join(x['categories'])}**", "", "## Important", "Scores are discovery signals, not proof of profitability. Payment claims require independent verification.", "", "## Evidence"]
    for e in evidence:
        lines += [f"### {e['source']} — {e['title']}", f"Confidence: {e['confidence']} | Verified: {bool(e['verified'])}", f"URL: {e['url']}", "", e["text"][:2500], ""]
    lines += ["## Rebuild hypotheses", "1. Identify the exact customer-facing output.", "2. Identify required tools, data and APIs.", "3. Rebuild capabilities independently and respect licenses/terms.", "4. Define deterministic acceptance tests.", "5. Test with non-paying/local fixtures first.", "6. Only later evaluate bidding/execution under explicit controls.", "7. Measure revenue, execution cost, rejection rate and time per job."]
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


def collect() -> tuple[int, int]:
    c = conn()
    imported = ingest_seed_findings(c)
    mb = 0
    try:
        items = moltbook.collect_rss()
        raw = json.dumps(items, ensure_ascii=False, indent=2)
        (RAW / "moltbook_rss.json").write_text(raw, encoding="utf-8")
        for item in items:
            eid, created = insert_evidence(c, source="moltbook", title=item["title"], url=item["url"], author=item["author"], published=item["published"], text=item["text"], evidence_type="public_post", confidence="low", verified=False)
            if created:
                mb += 1
            if item["author"]:
                upsert_agent(c, item["author"], item["url"], "moltbook")
    except Exception as ex:
        print("[WARN] Moltbook:", ex)
    mj = 0
    try:
        jobs = moltjobs.pages()
        (RAW / "moltjobs_open_jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
        for j in jobs:
            title = str(j.get("title") or j.get("name") or "MoltJobs job")
            url = str(j.get("url") or j.get("webUrl") or f"https://moltjobs.io/jobs/{stable_job_key(j).replace('sha256:','')}")
            author = str(j.get("agentId") or "")
            text = "\n".join(str(j.get(k, "")) for k in ("title", "description", "requirements", "outputSchema", "budget", "currency", "purpose", "participationMode"))
            eid, created = insert_evidence(c, source="moltjobs", external_id=stable_job_key(j), title=title, url=url, author=author, published=str(j.get("createdAt", "")), text=text or json.dumps(j, ensure_ascii=False), evidence_type="open_job", confidence="high", verified=False)
            if created:
                mj += 1
            # OPEN jobs are demand-side evidence; do not create a fake earning agent from agentId.
    except Exception as ex:
        print("[WARN] MoltJobs:", ex)
    c.commit()
    return imported + mb, mj


def scout() -> None:
    print("== AGENT FACTORY v0.2 ==")
    imported, jobs = collect()
    c = conn()
    xs = rebuild_candidates(c)
    for x in xs[:100]:
        blueprint(c, x)
    c.commit()
    print(f"New/seed evidence imported: {imported}")
    print(f"New MoltJobs observations: {jobs}")
    print("Evidence:", c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0])
    print("Agents:", c.execute("SELECT COUNT(*) FROM agents").fetchone()[0])
    print("Candidates:", len(xs))
    for x in xs[:10]:
        print(f"{x['earning_score']:>3} earn | {x['capability_score']:>3} cap | {x['confidence']:<6} | {x['name']:<30} | {','.join(x['categories'])}")


def verify_sources() -> None:
    print("== SOURCE VERIFICATION ==")
    for label, fn in [("Moltbook RSS", moltbook.collect_rss), ("MoltJobs OPEN", lambda: moltjobs.pages())]:
        try:
            result = fn()
            print(f"[OK] {label}: {len(result)} records")
        except Exception as ex:
            print(f"[FAIL] {label}: {type(ex).__name__}: {ex}")


def report() -> None:
    c = conn()
    rows = c.execute("""SELECT a.name,a.profile_url,c.earning_score,c.capability_score,c.confidence,c.categories,c.evidence_count,c.payment_count
        FROM candidates c JOIN agents a ON a.id=c.agent_id ORDER BY c.earning_score DESC,c.capability_score DESC LIMIT 25""").fetchall()
    if not rows:
        print("No candidates. Run: python -m agent_factory scout")
        return
    print("== AGENT INTELLIGENCE ==")
    for r in rows:
        print(f"\n[{r['earning_score']} earn / {r['capability_score']} cap] {r['name']} ({r['confidence']})")
        print(f"Categories: {r['categories']} | Evidence: {r['evidence_count']} | Payments: {r['payment_count']}")
        print(r['profile_url'] or "")
