from __future__ import annotations
import json
import hashlib
from urllib.parse import quote
from .common import get

BASE = "https://api.moltjobs.io/v1"
ALLOWED = {"api.moltjobs.io"}


def _payload(r):
    if "json" not in (r.headers.get("content-type") or "").lower():
        raise RuntimeError("MoltJobs returned non-JSON content")
    d = r.json()
    if not isinstance(d, dict):
        raise RuntimeError("MoltJobs response is not an object")
    jobs = d.get("data", d.get("jobs", []))
    if not isinstance(jobs, list):
        raise RuntimeError("MoltJobs data is not a list")
    meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
    return jobs, meta


def pages(limit: int = 100, max_pages: int = 20) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    cursor = None
    for _ in range(max_pages):
        url = f"{BASE}/jobs?status=OPEN&limit={min(limit,100)}"
        if cursor:
            url += "&cursor=" + quote(str(cursor), safe="")
        r = get(url, api_key_env="MOLTJOBS_API_KEY", allowed_hosts=ALLOWED, min_delay=1.0)
        jobs, meta = _payload(r)
        for j in jobs:
            if not isinstance(j, dict):
                continue
            jid = str(j.get("id") or j.get("jobId") or "").strip()
            key = jid or "sha256:" + hashlib.sha256(json.dumps(j, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            if key not in seen:
                seen.add(key)
                out.append(j)
        cursor = meta.get("nextCursor")
        if not cursor:
            return out
    raise RuntimeError(f"MoltJobs pagination exceeded max_pages={max_pages}")


def job_text(j: dict) -> str:
    keys = ("title", "name", "description", "requirements", "acceptanceCriteria", "outputSchema", "budgetUsdc", "chainId", "paymentProvider", "escrowTxHash", "escrowJobId", "paymentStatus", "status", "vertical")
    parts = []
    for k in keys:
        v = j.get(k)
        if v not in (None, "", [], {}):
            parts.append(f"{k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}")
    return "\n".join(parts) or json.dumps(j, ensure_ascii=False)
