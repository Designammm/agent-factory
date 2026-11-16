from __future__ import annotations
import json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import feedparser, requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
DATA, RAW, REPORTS = ROOT/"data", ROOT/"data/raw", ROOT/"reports"
DB = DATA/"agent_factory.db"
for p in (DATA, RAW, REPORTS): p.mkdir(parents=True, exist_ok=True)
UA = "AgentFactory/0.1 (local research scout)"

def conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS evidence(
        id INTEGER PRIMARY KEY, source TEXT, title TEXT, url TEXT, author TEXT,
        published TEXT, text TEXT, fetched_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS candidates(
        id INTEGER PRIMARY KEY, name TEXT, url TEXT, score INTEGER,
        category TEXT, evidence TEXT, blueprint TEXT, updated_at TEXT)""")
    c.commit()
    return c

def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text

def save(c, source, title, url, author, published, text):
    if not text.strip(): return
    if c.execute("SELECT 1 FROM evidence WHERE source=? AND url=?", (source,url)).fetchone():
        return
    c.execute("INSERT INTO evidence(source,title,url,author,published,text,fetched_at) VALUES(?,?,?,?,?,?,?)",
              (source,title,url,author,published,text[:50000],datetime.now(timezone.utc).isoformat()))

def collect_moltbook(c):
    for u in CFG["sources"]["moltbook_feeds"]:
        try:
            raw = fetch(u)
            (RAW/("moltbook_rss.xml" if "rss" in u else "moltbook_atom.xml")).write_text(raw, encoding="utf-8")
            f = feedparser.parse(raw)
            for e in f.entries:
                title = e.get("title","")
                summary = BeautifulSoup(e.get("summary",""),"html.parser").get_text(" ",strip=True)
                content = " ".join(BeautifulSoup(x.get("value",""),"html.parser").get_text(" ",strip=True)
                                   for x in e.get("content",[]))
                save(c,"moltbook",title,e.get("link",""),e.get("author",""),e.get("published",""),
                     f"{title}\n{summary}\n{content}")
        except Exception as ex:
            print("[WARN] Moltbook:", ex)

def collect_moltjobs(c):
    u = CFG["sources"]["moltjobs_open_jobs"]
    try:
        raw = fetch(u)
        (RAW/"moltjobs_open_jobs.json").write_text(raw, encoding="utf-8")
        d = json.loads(raw)
        jobs = d.get("data", d)
        if isinstance(jobs, dict): jobs = jobs.get("jobs", [])
        if not isinstance(jobs, list): jobs=[]
        for j in jobs:
            title=j.get("title") or j.get("name") or "MoltJobs job"
            url=j.get("url") or j.get("webUrl") or f"https://moltjobs.io/jobs/{j.get('id','')}"
            save(c,"moltjobs",title,url,j.get("agentId",""),j.get("createdAt",""),
                 json.dumps(j,ensure_ascii=False))
    except Exception as ex:
        print("[WARN] MoltJobs:", ex)

def score(text):
    t=text.lower(); s=0; ev=[]; risks=[]
    if any(x in t for x in CFG["money"]): s+=3; ev.append("money/work signal")
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:usdc|usd|near)\b",t): s+=8; ev.append("explicit payment amount")
    if any(x in t for x in CFG["work"]): s+=3; ev.append("repeatable digital work")
    if any(x in t for x in CFG["automation"]): s+=2; ev.append("automation signal")
    if any(x in t for x in ["escrow","on-chain","wallet","paid on approval"]): s+=2; ev.append("payout mechanism")
    if "github.com" in t or "open source" in t or "opensource" in t: s+=2; ev.append("public code/reference")
    for x in CFG["risk"]:
        if x in t: s-=8; risks.append(x)
    return s, ev, risks

def category(text):
    t=text.lower()
    groups={
        "research":["research","market research","report"],
        "data":["data extraction","scraping","classification","csv"],
        "software":["python","javascript","typescript","bug","api integration"],
        "content":["content","article","copywriting"],
        "qa":["qa","testing","test coverage","bug reproduction"],
        "lead_gen":["lead gen","leads","prospecting"]
    }
    for k, terms in groups.items():
        if any(x in t for x in terms): return k
    return "unknown"

def name(title,author,url):
    x=author.strip() or title.strip() or urlparse(url).path.rsplit("/",1)[-1]
    x=re.sub(r"[^a-zA-Z0-9 _-]+","",x).strip()
    return x[:70] or "unknown-agent"

def build(c):
    rows=c.execute("SELECT source,title,url,author,published,text FROM evidence").fetchall()
    out=[]
    for source,title,url,author,published,text in rows:
        s,ev,risks=score(text)
        if s<5: continue
        out.append({
            "name":name(title,author,url),"url":url,"score":s,
            "category":category(text),"evidence":"; ".join(ev),
            "risks":", ".join(risks),"excerpt":text[:1500].replace("\n"," ")
        })
    best={}
    for x in out:
        key=x["url"] or x["name"]
        if key not in best or x["score"]>best[key]["score"]: best[key]=x
    return sorted(best.values(),key=lambda x:x["score"],reverse=True)

def blueprint(x):
    slug=re.sub(r"[^a-z0-9]+","-",x["name"].lower()).strip("-")[:60] or "candidate"
    p=REPORTS/f"{slug}.md"
    p.write_text(f"""# Agent Blueprint: {x["name"]}

Score: **{x["score"]}**
Category: **{x["category"]}**
Source: {x["url"]}

## Evidence detected
{x["evidence"]}

## Risk signals
{x["risks"] or "None detected by the simple rule set."}

## Observed public pattern
{x["excerpt"]}

## Rebuild plan
1. Identify the exact customer-facing output.
2. Identify the job source and public/API interface.
3. Identify required tools and data sources.
4. Build an independent implementation.
5. Add deterministic validation against acceptance criteria.
6. Test with low-value jobs before autonomous bidding.
7. Track revenue, execution cost, rejection rate and time per job.

This is an architectural hypothesis, not proof of profitability.
""",encoding="utf-8")
    return str(p)

def scout():
    c=conn()
    print("== AGENT FACTORY v0.1 ==")
    collect_moltbook(c); collect_moltjobs(c); c.commit()
    xs=build(c)
    c.execute("DELETE FROM candidates")
    for x in xs[:100]:
        p=blueprint(x)
        c.execute("""INSERT INTO candidates(name,url,score,category,evidence,blueprint,updated_at)
                     VALUES(?,?,?,?,?,?,?)""",
                  (x["name"],x["url"],x["score"],x["category"],x["evidence"],p,
                   datetime.now(timezone.utc).isoformat()))
    c.commit()
    print("Evidence:",c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0])
    print("Candidates:",len(xs))
    for x in xs[:10]:
        print(f"{x['score']:>3} | {x['category']:<10} | {x['name']:<35} | {x['url']}")

def report():
    c=conn()
    rows=c.execute("""SELECT name,score,category,url,evidence,blueprint
                      FROM candidates ORDER BY score DESC LIMIT 25""").fetchall()
    if not rows:
        print("No candidates. Run: python -m agent_factory scout"); return
    print("== TOP CANDIDATES ==")
    for name_,score_,cat,url,ev,bp in rows:
        print(f"\n[{score_}] {name_} / {cat}\n{url}\n{ev}\n{bp}")
