from types import SimpleNamespace
import pytest
import requests
from agent_factory.sources import common, moltjobs, moltbook


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code=status
        self._payload=payload
        self.headers=headers or {"content-type":"application/json"}
    def json(self): return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_get_retries_retryable_status(monkeypatch):
    calls=[]
    responses=[FakeResponse(503),FakeResponse(200,{"ok":True})]
    monkeypatch.setattr(common.requests,"get",lambda *a,**k:(calls.append(a[0]) or responses.pop(0)))
    monkeypatch.setattr(common.time,"sleep",lambda _:None)
    r=common.get("https://example.com/api",retries=1,min_delay=0,allowed_hosts={"example.com"})
    assert r.status_code==200 and len(calls)==2


def test_get_blocks_redirect_to_disallowed_host(monkeypatch):
    monkeypatch.setattr(common.requests,"get",lambda *a,**k:FakeResponse(302,headers={"Location":"https://evil.example/pwn"}))
    with pytest.raises(common.SourceError,match="Blocked external URL"):
        common.get("https://example.com/api",allowed_hosts={"example.com"},retries=0)


def test_get_allows_same_host_relative_redirect(monkeypatch):
    calls=[]
    responses=[FakeResponse(302,headers={"Location":"/next"}),FakeResponse(200,{"ok":True})]
    monkeypatch.setattr(common.requests,"get",lambda *a,**k:(calls.append(a[0]) or responses.pop(0)))
    r=common.get("https://example.com/api",allowed_hosts={"example.com"},retries=0)
    assert r.status_code==200 and calls==["https://example.com/api","https://example.com/next"]


def test_moltjobs_pagination_terminates(monkeypatch):
    payloads=[FakeResponse(200,{"data":[{"id":"a"}],"meta":{"nextCursor":"b"}}),FakeResponse(200,{"data":[{"id":"b"}],"meta":{"nextCursor":None}})]
    monkeypatch.setattr(moltjobs,"get",lambda *a,**k:payloads.pop(0))
    assert [x["id"] for x in moltjobs.pages(limit=100,max_pages=2)]==["a","b"]


def test_moltjobs_pagination_cap_raises(monkeypatch):
    payload=FakeResponse(200,{"data":[{"id":"same"}],"meta":{"nextCursor":"again"}})
    monkeypatch.setattr(moltjobs,"get",lambda *a,**k:payload)
    with pytest.raises(RuntimeError,match="pagination exceeded"):
        moltjobs.pages(limit=100,max_pages=2)


def test_moltjobs_missing_ids_use_deterministic_sha256():
    from agent_factory.core import stable_job_key
    assert stable_job_key({"title":"A","description":"B"}).startswith("sha256:")


def test_moltbook_parser_rejects_unusable_payload():
    with pytest.raises(RuntimeError,match="no post list"):
        moltbook._records({"unexpected":{}})
