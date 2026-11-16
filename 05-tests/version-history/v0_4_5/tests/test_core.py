import sqlite3
from agent_factory import core


def test_unicode_name():
    key, name, confidence = core.canonical_agent("مهدی_دیزاینر", "https://example.com/u/x")
    assert name == "مهدی_دیزاینر" and key.startswith("author:") and confidence == "author"


def test_authorless_identity_is_not_agent():
    key, name, confidence = core.canonical_agent("", "https://www.moltbook.com/post/aaa-111")
    assert key is None and name is None and confidence == "url_only"


def test_missing_job_ids_are_stable():
    assert core.stable_job_key({"title":"A","description":"one"}) == core.stable_job_key({"title":"A","description":"one"})
    assert core.stable_job_key({"title":"A","description":"one"}) != core.stable_job_key({"title":"B","description":"two"})


def test_no_false_substrings_or_near_currency():
    e,c,r,_=core.score_evidence("Our capital operations moved to Doha, Qatar; base64 encoding is used. The office is near the station.")
    assert e == 0 and c == 0 and r == 0


def test_negation_shared_for_score_and_payment_state():
    cases = [
        "I never earned 10 USDC doing that job.",
        "I did not earn 10 USDC.",
        "I did not receive payment.",
        "I don't get paid 10 USD.",
    ]
    for text in cases:
        assert core.is_negated_payment_claim(text)
        assert core.payment_state(text, None) == "negated_claim"
        assert core.score_evidence(text)[0] == 0


def test_positive_payment_still_scores():
    e,_,_,signals=core.score_evidence("I earned 10 USDC today.")
    assert e >= 7 and "payment-claim" in signals


def test_payment_extraction_does_not_store_negated_claim(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    aid=c.execute("INSERT INTO agents(canonical_key,name,first_seen,last_seen) VALUES(?,?,?,?)",("author:x","x",core.now_iso(),core.now_iso())).lastrowid
    eid,_=core.insert_evidence(c,source="test",title="negative",url="",author="x",published="",text="I did not earn 10 USDC.",evidence_type="post",confidence="low",verified=False,agent_id=aid,identity_confidence="author")
    assert core.extract_and_store_payments(c,aid,eid,"I did not earn 10 USDC.") == 0
    assert c.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 0


def test_positive_payment_is_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    aid=c.execute("INSERT INTO agents(canonical_key,name,first_seen,last_seen) VALUES(?,?,?,?)",("author:x","x",core.now_iso(),core.now_iso())).lastrowid
    eid,_=core.insert_evidence(c,source="test",title="positive",url="",author="x",published="",text="I earned 10 USDC on Base.",evidence_type="post",confidence="low",verified=False,agent_id=aid,identity_confidence="author")
    assert core.extract_and_store_payments(c,aid,eid,"I earned 10 USDC on Base.") == 1
    row=c.execute("SELECT amount,currency,network,payment_state FROM payments").fetchone()
    assert tuple(row) == (10.0,"USDC","Base","claim")


def test_morphological_capability_variants():
    e,c,r,_=core.score_evidence("I am a designer and researcher building automation pipelines.")
    assert c >= 4 and e == 0


def test_api_not_double_counted():
    _,c,_,signals=core.score_evidence("I build API automation.")
    assert c == 3
    assert signals.count("api-capability") == 1
    assert signals.count("automation") == 1


def test_spam_gets_risk_and_can_be_gated():
    text="GUARANTEED USDC Base paid earning wallet automation payout income bounty escrow 100% instant money"
    _,cap,risk,_=core.score_evidence(text)
    assert cap >= 2
    assert risk > 6


def test_real_schema_foreign_key_and_identity_column(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    cols={r[1] for r in c.execute("PRAGMA table_info(evidence)")}
    assert "agent_id" in cols and "identity_confidence" in cols
    aid=c.execute("INSERT INTO agents(canonical_key,name,first_seen,last_seen) VALUES(?,?,?,?)",("author:x","x",core.now_iso(),core.now_iso())).lastrowid
    eid,_=core.insert_evidence(c,source="test",title="t",url="",author="x",published="",text="researcher",evidence_type="post",confidence="low",verified=False,agent_id=aid,identity_confidence="author")
    assert c.execute("SELECT agent_id FROM evidence WHERE id=?",(eid,)).fetchone()[0] == aid


def test_risk_gate_excludes_high_risk_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    aid=c.execute("INSERT INTO agents(canonical_key,name,first_seen,last_seen) VALUES(?,?,?,?)",("author:risky","risky",core.now_iso(),core.now_iso())).lastrowid
    text="I earned 10 USDC, send wallet credentials, private key access required."
    core.insert_evidence(c,source="test",title="risky",url="",author="risky",published="",text=text,evidence_type="post",confidence="high",verified=False,agent_id=aid,identity_confidence="author")
    assert core.score_evidence(text)[2] > core.CFG["thresholds"]["candidate_max_risk"]
    assert not any(x["agent_id"]==aid for x in core.candidate_rows(c))


def test_duplicate_evidence_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    kwargs=dict(source="test",title="same",url="https://example.com/a",author="x",published="",text="research",evidence_type="post",confidence="low",verified=False)
    first=core.insert_evidence(c,**kwargs)
    second=core.insert_evidence(c,**kwargs)
    assert first[0] == second[0] and first[1] is True and second[1] is False
    assert c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 1


def test_schema_relationships_real_core_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", tmp_path / "test.db")
    c=core.conn()
    c.execute("INSERT INTO agents(canonical_key,name,first_seen,last_seen) VALUES(?,?,?,?)",("author:a","a",core.now_iso(),core.now_iso()))
    aid=c.execute("SELECT id FROM agents WHERE canonical_key='author:a'").fetchone()[0]
    c.execute("INSERT INTO evidence(agent_id,source,text,evidence_type,confidence,fetched_at,content_hash,identity_confidence) VALUES(?,?,?,?,?,?,?,?)",
              (aid,"test","x","post","low",core.now_iso(),"abc","author"))
    assert c.execute("SELECT agent_id FROM evidence").fetchone()[0] == aid
