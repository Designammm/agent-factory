import sqlite3
from pathlib import Path
from agent_factory.core import canonical_agent, category_set, extract_payment, extract_tx_hash, payment_state, score_evidence, stable_job_key, is_negated_payment_claim, extract_and_store_payments, conn, candidate_rows


def test_unicode_name():
    key, name, identity = canonical_agent("مهدی_دیزاینر", "https://example.com/u/x")
    assert name == "مهدی_دیزاینر" and key.startswith("author:") and identity == "author"


def test_authorless_url_is_not_pseudo_agent():
    key, name, identity = canonical_agent("", "https://www.moltbook.com/post/aaa-111")
    assert key is None and name is None and identity == "url_only"


def test_missing_job_ids_are_stable_and_unique():
    assert stable_job_key({"title": "A", "description": "one"}) != stable_job_key({"title": "B", "description": "two"})


def test_no_false_money_or_coding_substrings():
    e, c, r, _ = score_evidence("Our capital operations moved to Doha, Qatar; base64 encoding is used.")
    assert e == 0 and c == 0 and r == 0


def test_near_english_word_is_not_currency():
    e, _, _, _ = score_evidence("The office is near the station.")
    assert e == 0


def test_unpaid_job_is_not_earnings():
    e, _, _, _ = score_evidence("unpaid task status OPEN jobId 123 agentId null")
    assert e == 0


def test_negated_payment_claim_variants_are_not_earnings():
    for text in [
        "I did not earn 10 USDC.",
        "I never earned 10 USDC.",
        "I do not receive payment.",
        "I did not receive payment and there is no transaction proof.",
    ]:
        e, _, _, _ = score_evidence(text)
        assert e == 0, text
        assert is_negated_payment_claim(text), text


def test_negated_payment_is_not_persisted():
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE payments(id INTEGER PRIMARY KEY, agent_id INTEGER, evidence_id INTEGER, amount REAL, currency TEXT, network TEXT, tx_hash TEXT, verification TEXT, payment_state TEXT, observed_at TEXT, payment_key TEXT UNIQUE)")
    assert extract_and_store_payments(c, 1, 1, "I never earned 10 USDC") == 0
    assert c.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0


def test_positive_payment_claim_is_persisted():
    c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE payments(id INTEGER PRIMARY KEY, agent_id INTEGER, evidence_id INTEGER, amount REAL, currency TEXT, network TEXT, tx_hash TEXT, verification TEXT, payment_state TEXT, observed_at TEXT, payment_key TEXT UNIQUE)")
    assert extract_and_store_payments(c, 1, 1, "I earned 10 USDC") == 1
    row = c.execute("SELECT amount,currency,payment_state FROM payments").fetchone()
    assert tuple(row) == (10.0, "USDC", "claim")


def test_payment_claim_vs_tx_evidence():
    assert payment_state("I earned 10 USDC, no tx proof", None) == "negated_claim"
    tx = "0x" + "a" * 64
    assert extract_tx_hash("paid 10 USDC on Base tx " + tx) == tx
    assert payment_state("paid 10 USDC on Base tx " + tx, tx) == "evidence_pending_verification"


def test_payment_extraction():
    assert extract_payment("received 0.05 USDC on Base") == (.05, "USDC", "Base")


def test_categories_cover_morphological_variants():
    cats = category_set("I am a designer and researcher; I build Python automation and run testing.")
    assert set(cats) >= {"research", "software", "qa"}


def test_real_schema_relationships():
    c = conn()
    cols = {r[1] for r in c.execute("PRAGMA table_info(evidence)")}
    assert {"agent_id", "identity_confidence"} <= cols
    pcols = {r[1] for r in c.execute("PRAGMA table_info(payments)")}
    assert {"payment_state", "payment_key"} <= pcols
    assert c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "4"
    c.close()


def test_risk_is_nonzero_for_wallet_credential_language():
    _, _, risk, _ = score_evidence("I can provide private key access and wallet credentials")
    assert risk > 0


def test_spam_hype_has_risk():
    _, _, risk, _ = score_evidence("GUARANTEED USDC Base paid earning wallet automation payout income!!")
    assert risk > 0


def test_risk_gate_excludes_high_risk_candidate():
    c = conn()
    c.execute("DELETE FROM candidates")
    c.execute("DELETE FROM payments")
    c.execute("DELETE FROM observations")
    c.execute("DELETE FROM evidence")
    c.execute("DELETE FROM agents")
    c.execute("INSERT INTO agents(canonical_key,name,source,first_seen,last_seen) VALUES(?,?,?,?,?)", ("author:risky", "risky", "test", "now", "now"))
    aid = c.execute("SELECT id FROM agents WHERE canonical_key='author:risky'").fetchone()[0]
    c.execute("INSERT INTO evidence(agent_id,source,title,url,author,published,text,evidence_type,confidence,verified,fetched_at,content_hash,identity_confidence) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (aid,"test","x","","risky","","GUARANTEED private key access USDC paid payout income trading gambling","test","low",0,"now","risk-test","author"))
    c.commit()
    assert all(x["name"] != "risky" for x in candidate_rows(c))
    c.close()


def test_v3_to_v4_migration_cleans_legacy_rows(tmp_path, monkeypatch):
    import agent_factory.core as core
    db = tmp_path / "legacy.db"
    monkeypatch.setattr(core, "DB", db)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    c.execute("CREATE TABLE agents(id INTEGER PRIMARY KEY, canonical_key TEXT UNIQUE, name TEXT, profile_url TEXT, source TEXT, first_seen TEXT, last_seen TEXT)")
    c.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, agent_id INTEGER, source TEXT, external_id TEXT, title TEXT, url TEXT, author TEXT, published TEXT, text TEXT, evidence_type TEXT, confidence TEXT, verified INTEGER, fetched_at TEXT, content_hash TEXT)")
    c.execute("CREATE TABLE payments(id INTEGER PRIMARY KEY, agent_id INTEGER, evidence_id INTEGER, amount REAL, currency TEXT, network TEXT, tx_hash TEXT, verification TEXT, payment_state TEXT, observed_at TEXT, payment_key TEXT)")
    c.execute("CREATE TABLE observations(id INTEGER PRIMARY KEY, agent_id INTEGER, evidence_id INTEGER, claim_type TEXT, value_json TEXT, confidence TEXT, created_at TEXT)")
    c.execute("CREATE TABLE candidates(id INTEGER PRIMARY KEY, agent_id INTEGER, earning_score INTEGER, capability_score INTEGER, risk_score INTEGER, confidence TEXT, categories TEXT, evidence_count INTEGER, payment_count INTEGER, verified_payment_count INTEGER, updated_at TEXT)")
    c.execute("INSERT INTO agents VALUES(1,'url:https://www.moltbook.com/post/legacy','legacy','https://www.moltbook.com/post/legacy','moltbook','now','now')")
    c.execute("INSERT INTO evidence VALUES(1,1,'moltbook','1','legacy','https://www.moltbook.com/post/legacy','','','I never earned 10 USDC','public_post','low',0,'now','legacyhash')")
    c.execute("INSERT INTO payments VALUES(1,1,1,10,'USDC','Base',NULL,'unverified','claim','now','legacy-pay')")
    c.commit(); c.close()

    c = core.conn()
    assert c.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0
    assert c.execute("SELECT COUNT(*) FROM agents WHERE canonical_key LIKE 'url:%'").fetchone()[0] == 0
    assert tuple(c.execute("SELECT agent_id,identity_confidence FROM evidence WHERE id=1").fetchone()) == (None, "url_only")
    assert c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "4"
    c.close()
