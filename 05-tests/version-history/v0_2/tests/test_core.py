import json
import sqlite3
from pathlib import Path

from agent_factory.core import canonical_agent, category_set, extract_payment, hash_text, stable_job_key, score_evidence


def test_persian_agent_name_is_preserved():
    key, name = canonical_agent("مهدی_دیزاینر", "https://example.com/u/x")
    assert name == "مهدی_دیزاینر"
    assert key.startswith("author:")


def test_job_fallback_is_unique():
    a = {"title": "A", "description": "one"}
    b = {"title": "B", "description": "two"}
    assert stable_job_key(a) != stable_job_key(b)


def test_substring_false_positive_is_removed():
    earning, capability, _, _ = score_evidence("Our research subsidiary moved its capital operations to Doha, Qatar this quarter.")
    assert earning == 0
    assert capability == 2


def test_job_field_name_does_not_create_money_signal():
    text = "title: extract data\ndescription: unpaid task\nstatus: OPEN\njobId: 123\nagentId: null"
    earning, _, _, _ = score_evidence(text)
    assert earning == 0


def test_payment_extraction():
    assert extract_payment("received 0.05 USDC on Base") == (0.05, "USDC", "Base")


def test_multi_category():
    cats = category_set("Python research report and data extraction with QA testing")
    assert set(cats) >= {"research", "data", "software", "qa"}
