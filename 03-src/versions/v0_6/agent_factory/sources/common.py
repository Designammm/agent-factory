from __future__ import annotations
import os
import random
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import requests

UA = "AgentFactory/0.5.0 (local research scout)"
RETRYABLE = {429, 500, 502, 503, 504}

class SourceError(RuntimeError):
    pass

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _headers(api_key_env: str | None) -> dict[str, str]:
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if api_key_env:
        key = os.getenv(api_key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
    return headers

def get(url: str, *, api_key_env: str | None = None, timeout: int = 10,
        retries: int = 2, min_delay: float = 1.0, allowed_hosts: set[str] | None = None) -> requests.Response:
    assert_allowed_url(url, allowed_hosts or set())
    last = None
    for attempt in range(retries + 1):
        if attempt:
            time.sleep(min(8.0, min_delay * (2 ** (attempt - 1))) + random.random() * 0.25)
        try:
            r = requests.get(url, headers=_headers(api_key_env), timeout=timeout, allow_redirects=False)
            if r.status_code in RETRYABLE and attempt < retries:
                last = SourceError(f"HTTP {r.status_code}")
                continue
            if 300 <= r.status_code < 400:
                loc = r.headers.get("Location", "")
                if not loc:
                    raise SourceError(f"Redirect without Location: {url}")
                loc = urljoin(url, loc)
                assert_allowed_url(loc, allowed_hosts or set())
                r = requests.get(loc, headers=_headers(api_key_env), timeout=timeout, allow_redirects=False)
            r.raise_for_status()
            return r
        except requests.RequestException as ex:
            last = ex
            if attempt >= retries:
                raise SourceError(f"GET failed: {url}: {ex}") from ex
    raise SourceError(f"GET failed: {url}: {last}")

def assert_allowed_url(url: str, allowed_hosts: set[str]) -> None:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or host not in {h.lower() for h in allowed_hosts}:
        raise SourceError(f"Blocked external URL: {url}")
