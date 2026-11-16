from __future__ import annotations
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
from .common import get, assert_allowed_url

RSS_URL = "https://moltbook.com/m/rss"
API_BASE = "https://www.moltbook.com/api/v1"


def _text(node, tag: str) -> str:
    child = node.find(tag)
    return "" if child is None else "".join(child.itertext()).strip()


def collect_rss() -> list[dict]:
    assert_allowed_url(RSS_URL, {"moltbook.com", "www.moltbook.com"})
    r = get(RSS_URL, api_key_env="MOLTBOOK_API_KEY")
    ctype = (r.headers.get("content-type") or "").lower()
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as ex:
        raise RuntimeError(f"Moltbook RSS/XML parse failure; content-type={ctype}") from ex

    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//entry")
    if not entries:
        raise RuntimeError(f"Moltbook RSS returned zero entries; content-type={ctype}")

    out = []
    for e in entries:
        title = _text(e, "title")
        summary = _text(e, "description") or _text(e, "summary")
        link = _text(e, "link")
        if not link:
            link_node = e.find("link")
            if link_node is not None:
                link = link_node.attrib.get("href", "")
        author = _text(e, "author") or _text(e, "dc:creator")
        published = _text(e, "pubDate") or _text(e, "published") or _text(e, "updated")
        text = "\n".join(x for x in [title, BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)] if x)
        out.append({"title": title, "url": link, "author": author, "published": published, "text": text})
    return out
