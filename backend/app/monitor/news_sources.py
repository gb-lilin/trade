from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) QuantTradeV5/1.0",
    "Accept": "application/rss+xml, application/xml, text/xml, application/json, text/html,*/*",
}


@dataclass
class RawNewsItem:
    title: str
    summary: str
    url: str
    source: str
    published_at: str | None = None


# (展示名, RSS URL) — 与 DEFAULT_RSS 及 env 自定义源配合使用
LABELED_RSS_FEEDS: list[tuple[str, str]] = [
    ("华尔街日报", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("华尔街日报", "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
    ("新浪财经", "https://rss.sina.com.cn/roll/finance/hot_roll.xml"),
    ("新浪财经", "https://rss.sina.com.cn/finance/jsy.xml"),
    ("中国新闻网", "https://www.chinanews.com.cn/rss/finance.xml"),
    ("人民网", "https://www.people.com.cn/rss/finance.xml"),
    ("财联社", "https://feedx.net/rss/cls.xml"),
    ("华尔街见闻", "https://feedx.net/rss/wallstreetcn.xml"),
]

RSS_LABEL_BY_HOST: dict[str, str] = {
    "feedx.net": "财经聚合",
    "feeds.a.dj.com": "华尔街日报",
    "rss.sina.com.cn": "新浪财经",
    "www.chinanews.com.cn": "中国新闻网",
    "www.people.com.cn": "人民网",
}


async def fetch_all_sources(client: httpx.AsyncClient, limit_per_source: int = 12) -> tuple[list[RawNewsItem], dict[str, Any]]:
    import asyncio

    tasks = [
        _safe_fetch("东方财富网", fetch_eastmoney(client, limit_per_source)),
        _safe_fetch("央视新闻", fetch_cctv_finance(client, limit_per_source)),
    ]
    for label, url in LABELED_RSS_FEEDS:
        timeout = 6.0 if "feedx.net" in url else 12.0
        tasks.append(_safe_fetch(label, fetch_rss(client, url, label, limit_per_source, timeout=timeout)))

    results = await asyncio.gather(*tasks)
    collected: list[RawNewsItem] = []
    stats: dict[str, Any] = {"ok": [], "failed": [], "counts": {}}
    for label, items, err in results:
        if err:
            stats["failed"].append({"source": label, "error": err})
            continue
        stats["ok"].append(label)
        stats["counts"][label] = len(items)
        collected.extend(items)
    return collected, stats


async def _safe_fetch(label: str, coro) -> tuple[str, list[RawNewsItem], str | None]:
    try:
        items = await coro
        return label, items, None
    except Exception as exc:
        return label, [], str(exc)[:120]


async def fetch_eastmoney(client: httpx.AsyncClient, limit: int) -> list[RawNewsItem]:
    trace = str(uuid.uuid4())
    url = (
        "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        f"?client=web&biz=web_news_col&column=350&order=1&needInteractData=0"
        f"&page_index=1&page_size={limit}&req_trace={trace}"
    )
    r = await client.get(
        url,
        headers={**_BROWSER_HEADERS, "Referer": "https://finance.eastmoney.com/"},
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != "1":
        raise RuntimeError(body.get("message") or "eastmoney api error")
    out: list[RawNewsItem] = []
    for row in (body.get("data") or {}).get("list") or []:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        summary = (row.get("summary") or title).strip()
        summary = re.sub(r"^【[^】]+】", "", summary).strip() or title
        link = (row.get("uniqueUrl") or row.get("url") or "").strip()
        pub = _parse_show_time(row.get("showTime") or "")
        out.append(
            RawNewsItem(
                title=title,
                summary=summary[:400],
                url=link,
                source="东方财富网",
                published_at=pub,
            )
        )
    return out


async def fetch_cctv_finance(client: httpx.AsyncClient, limit: int) -> list[RawNewsItem]:
    r = await client.get("https://finance.cctv.com/", headers=_BROWSER_HEADERS)
    r.raise_for_status()
    html = r.text
    pat = re.compile(
        r'href="(https://finance\.cctv\.com/\d{4}/\d{2}/\d{2}/ART[^"]+\.shtml)"[^>]*>([^<]{4,160})</a>',
        re.I,
    )
    seen: set[str] = set()
    out: list[RawNewsItem] = []
    for m in pat.finditer(html):
        url, title = m.group(1), _strip_html(m.group(2))
        if url in seen or len(title) < 6:
            continue
        seen.add(url)
        pub = _pub_from_cctv_url(url)
        out.append(
            RawNewsItem(
                title=title,
                summary=title,
                url=url,
                source="央视新闻",
                published_at=pub,
            )
        )
        if len(out) >= limit:
            break
    if not out:
        raise RuntimeError("未解析到央视财经列表")
    return out


async def fetch_rss(
    client: httpx.AsyncClient,
    url: str,
    label: str,
    limit: int,
    *,
    timeout: float = 12.0,
) -> list[RawNewsItem]:
    r = await client.get(url, headers={**_BROWSER_HEADERS, "User-Agent": "QuantTradeV5/1.0"}, timeout=timeout)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    channel = root.find("channel")
    entries = list(root.findall("entry"))
    if channel is not None:
        entries = channel.findall("item")
    if not entries and root.tag.endswith("feed"):
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")

    display = label or _label_from_rss_url(url)
    out: list[RawNewsItem] = []
    for node in entries[:limit]:
        title = _rss_text(node, "title")
        if not title:
            continue
        link = _rss_link(node)
        summary = _rss_text(node, "description") or _rss_text(node, "summary") or title
        summary = _strip_html(summary)[:400]
        pub = _rss_text(node, "pubDate") or _rss_text(node, "published") or _rss_text(node, "updated")
        out.append(
            RawNewsItem(
                title=title.strip(),
                summary=summary.strip(),
                url=link or "",
                source=display,
                published_at=_parse_rss_time(pub),
            )
        )
    return out


def _label_from_rss_url(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url)
    host = m.group(1) if m else ""
    return RSS_LABEL_BY_HOST.get(host, host or "RSS")


def _pub_from_cctv_url(url: str) -> str:
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if not m:
        return _now_iso()
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    dt = datetime(y, mo, d, 12, 0, 0, tzinfo=timezone.utc).astimezone()
    return dt.isoformat(timespec="seconds")


def _parse_show_time(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return _now_iso()
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).astimezone().isoformat(timespec="seconds")
    except ValueError:
        return _now_iso()


def _parse_rss_time(raw: str) -> str:
    if not raw:
        return _now_iso()
    try:
        return parsedate_to_datetime(raw).astimezone().isoformat(timespec="seconds")
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone().isoformat(timespec="seconds")
    except Exception:
        return _now_iso()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()


def _rss_text(node: ET.Element, tag: str) -> str:
    el = node.find(tag)
    if el is not None and el.text:
        return el.text
    el = node.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    return (el.text or "").strip() if el is not None else ""


def _rss_link(node: ET.Element) -> str:
    link = node.find("link")
    if link is not None:
        href = link.get("href") or (link.text or "")
        if href:
            return href.strip()
    guid = node.find("guid")
    if guid is not None and guid.text:
        return guid.text.strip()
    return ""
