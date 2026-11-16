from __future__ import annotations
import os
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests

UA = "AgentFactory/0.2 (local research scout; contact: local)"

class SourceError(RuntimeError):
    pass

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def get(url: str, *, api_key_env: str | None = None, timeout: int = 30) -> requests.Response:
    headers = {"User-Agent": UA, "Accept": "application/json, application/rss+xml, application/atom+xml, text/xml, text/html;q=0.9"}
    if api_key_env:
        key = os.getenv(api_key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
    r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r

def assert_allowed_url(url: str, allowed_hosts: set[str]) -> None:
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in allowed_hosts:
        raise SourceError(f"Blocked external URL: {url}")
