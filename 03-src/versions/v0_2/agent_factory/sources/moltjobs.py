from __future__ import annotations
import json
import os
from .common import get, assert_allowed_url, now_iso

BASE = "https://api.moltjobs.io/v1"
OPEN_URL = BASE + "/jobs?status=OPEN&limit=100"


def collect() -> tuple[list[dict], dict]:
    assert_allowed_url(OPEN_URL, {"api.moltjobs.io"})
    # Current public discovery is documented as readable without authentication.
    # If an authenticated key is supplied, it is sent automatically by common.get().
    r = get(OPEN_URL, api_key_env="MOLTJOBS_API_KEY")
    if "json" not in (r.headers.get("content-type") or "").lower():
        raise RuntimeError(f"MoltJobs returned non-JSON content type: {r.headers.get('content-type')}")
    d = r.json()
    jobs = d.get("data", []) if isinstance(d, dict) else []
    if not isinstance(jobs, list):
        raise RuntimeError("Unexpected MoltJobs response: data is not a list")
    meta = d.get("meta", {}) if isinstance(d, dict) else {}
    return jobs, {"url": r.url, "status": r.status_code, "meta": meta, "fetched_at": now_iso()}


def pages(limit: int = 100) -> list[dict]:
    """Fetch every OPEN page using nextCursor, deduplicating by stable job id."""
    seen: set[str] = set()
    out: list[dict] = []
    cursor = None
    while True:
        url = f"{BASE}/jobs?status=OPEN&limit={limit}"
        if cursor:
            from urllib.parse import quote
            url += "&cursor=" + quote(cursor, safe="")
        r = get(url, api_key_env="MOLTJOBS_API_KEY")
        if "json" not in (r.headers.get("content-type") or "").lower():
            raise RuntimeError("MoltJobs returned non-JSON content")
        d = r.json()
        jobs = d.get("data", []) if isinstance(d, dict) else []
        if not isinstance(jobs, list):
            raise RuntimeError("Unexpected MoltJobs data shape")
        for j in jobs:
            jid = str(j.get("id") or "")
            key = jid or json.dumps(j, sort_keys=True, ensure_ascii=False)
            if key not in seen:
                seen.add(key)
                out.append(j)
        meta = d.get("meta", {}) if isinstance(d, dict) else {}
        cursor = meta.get("nextCursor")
        if not cursor:
            break
    return out
