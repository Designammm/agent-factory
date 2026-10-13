from __future__ import annotations
from .common import get

API_BASE = "https://www.moltbook.com/api/v1"
ALLOWED = {"www.moltbook.com"}


def _records(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise RuntimeError("Moltbook response is not JSON object/list")
    for key in ("posts", "data", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    feed = payload.get("feed")
    if isinstance(feed, dict):
        for key in ("posts", "data", "items", "results"):
            if isinstance(feed.get(key), list):
                return feed[key]
    raise RuntimeError("Moltbook response contains no post list")


def _author(item: dict) -> str:
    a = item.get("author") or item.get("agent") or {}
    if isinstance(a, dict):
        return str(a.get("name") or a.get("username") or a.get("handle") or "").strip()
    return str(a).strip()


def _post_url(item: dict) -> str:
    return str(item.get("url") or item.get("webUrl") or item.get("permalink") or "").strip()


def collect(limit: int = 50) -> list[dict]:
    url = f"{API_BASE}/feed?sort=new&limit={limit}"
    r = get(url, api_key_env="MOLTBOOK_API_KEY", allowed_hosts=ALLOWED)
    payload = r.json()
    records = _records(payload)
    out = []
    for item in records:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        body = str(item.get("content") or item.get("body") or item.get("text") or item.get("description") or "").strip()
        if not (title or body):
            continue
        out.append({
            "external_id": str(item.get("id") or item.get("postId") or "").strip(),
            "title": title or "Moltbook post",
            "url": _post_url(item),
            "author": _author(item),
            "published": str(item.get("created_at") or item.get("createdAt") or item.get("published") or ""),
            "text": "\n".join(x for x in (title, body) if x),
            "raw": item,
        })
    if not out:
        raise RuntimeError("Moltbook feed returned zero usable posts")
    return out
