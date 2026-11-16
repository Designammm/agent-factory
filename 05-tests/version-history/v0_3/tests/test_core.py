import sqlite3
from agent_factory.core import canonical_agent, category_set, extract_payment, extract_tx_hash, payment_state, score_evidence, stable_job_key

def test_unicode_name():
    key,name=canonical_agent("مهدی_دیزاینر","https://example.com/u/x"); assert name=="مهدی_دیزاینر" and key.startswith("author:")

def test_missing_job_ids_are_stable_and_unique():
    assert stable_job_key({"title":"A","description":"one"}) != stable_job_key({"title":"B","description":"two"})

def test_no_false_money_or_coding_substrings():
    e,c,r,_=score_evidence("Our capital operations moved to Doha, Qatar; base64 encoding is used.")
    assert e==0 and c==0 and r==0

def test_unpaid_job_is_not_earnings():
    e,_,_,_=score_evidence("unpaid task status OPEN jobId 123 agentId null")
    assert e==0

def test_negated_payment_claim_is_not_payment_signal():
    e,_,_,_=score_evidence("I did not receive payment and there is no transaction proof.")
    assert e==0

def test_payment_claim_vs_tx_evidence():
    assert payment_state("I earned 10 USDC, no tx proof",None)=="unverified_claim"
    tx="0x"+"a"*64
    assert extract_tx_hash("paid 10 USDC on Base tx "+tx)==tx
    assert payment_state("paid 10 USDC on Base tx "+tx,tx)=="evidence_pending_verification"

def test_payment_extraction():
    assert extract_payment("received 0.05 USDC on Base")==(.05,"USDC","Base")

def test_categories_are_token_or_regex_based():
    cats=category_set("Python research report and data extraction with QA testing")
    assert set(cats)>={"research","data","software","qa"}

def test_schema_relationships():
    c=sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("CREATE TABLE agents(id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY,agent_id INTEGER REFERENCES agents(id))")
    c.execute("INSERT INTO agents VALUES(1)")
    c.execute("INSERT INTO evidence VALUES(1,1)")
    assert c.execute("SELECT agent_id FROM evidence WHERE id=1").fetchone()[0]==1

def test_risk_is_nonzero_for_wallet_credential_language():
    _,_,risk,_=score_evidence("I can provide private key access and wallet credentials")
    assert risk>0
