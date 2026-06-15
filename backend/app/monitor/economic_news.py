from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import settings


@dataclass
class EconomicNewsItem:
    id: str
    title: str
    summary: str
    source: str
    published_at: str
    url: str
    category: str = "macro"
    sentiment: str = "neutral"
    impact_score: float = 0.5
    ai_brief: str = ""
    pushed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_RSS = [
    "https://feedx.net/rss/cls.xml",
    "https://feedx.net/rss/wallstreetcn.xml",
]

_POS_KW = ("增长", "复苏", "利好", "上调", "超预期", "降准", "降息", "刺激", "回暖")
_NEG_KW = ("下滑", "衰退", "利空", "下调", "不及预期", "制裁", "违约", "暴跌", "收紧")
_MACRO_KW = ("GDP", "CPI", "PPI", "PMI", "央行", "国务院", "财政部", "美联储", "通胀", "就业")
_POLICY_KW = ("政策", "监管", "条例", "会议", "规划", "试点")
_MARKET_KW = ("A股", "沪深", "指数", "北向", "融资", "成交量", "涨停", "跌停")


class EconomicNewsService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or Path(__file__).resolve().parents[2] / "data" / "economic_news.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def _rss_urls(self) -> list[str]:
        raw = settings.news_rss_urls.strip()
        if not raw:
            return DEFAULT_RSS
        return [u.strip() for u in raw.split(",") if u.strip()]

    def load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"updated_at": None, "items": []}
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def save(self, items: list[EconomicNewsItem]) -> dict[str, Any]:
        payload = {
            "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "items": [i.to_dict() for i in items],
        }
        self.store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def list_items(self, limit: int = 30) -> dict[str, Any]:
        data = self.load()
        items = data.get("items", [])[:limit]
        return {"updated_at": data.get("updated_at"), "items": items, "count": len(items)}

    async def refresh(self, limit_per_feed: int = 15) -> dict[str, Any]:
        collected: list[EconomicNewsItem] = []
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            for url in self._rss_urls():
                try:
                    collected.extend(await self._fetch_rss(client, url, limit_per_feed))
                except Exception:
                    continue
        if not collected:
            collected = self._fallback_items()
        else:
            collected = self._dedupe(collected)

        enriched = [self._enrich_item(x) for x in collected[:50]]
        enriched.sort(key=lambda x: x.published_at, reverse=True)
        old = {x["id"]: x.get("pushed_at") for x in self.load().get("items", [])}
        for item in enriched:
            if item.id in old and old[item.id]:
                item.pushed_at = old[item.id]
        return self.save(enriched)

    async def _fetch_rss(self, client: httpx.AsyncClient, url: str, limit: int) -> list[EconomicNewsItem]:
        r = await client.get(url, headers={"User-Agent": "QuantTradeV5/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        channel = root.find("channel")
        entries = list(root.findall("entry"))
        if channel is not None:
            entries = channel.findall("item")
        if not entries and root.tag.endswith("feed"):
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")

        source = self._hostname(url)
        out: list[EconomicNewsItem] = []
        for node in entries[:limit]:
            title = self._text(node, "title")
            if not title:
                continue
            link = self._link(node)
            summary = self._text(node, "description") or self._text(node, "summary") or title
            summary = self._strip_html(summary)[:400]
            pub = self._text(node, "pubDate") or self._text(node, "published") or self._text(node, "updated")
            published_at = self._parse_time(pub)
            nid = hashlib.md5(f"{title}|{link}".encode()).hexdigest()[:16]
            out.append(
                EconomicNewsItem(
                    id=nid,
                    title=title.strip(),
                    summary=summary.strip(),
                    source=source,
                    published_at=published_at,
                    url=link or "",
                )
            )
        return out

    def _enrich_item(self, item: EconomicNewsItem) -> EconomicNewsItem:
        text = f"{item.title} {item.summary}"
        pos = sum(1 for k in _POS_KW if k in text)
        neg = sum(1 for k in _NEG_KW if k in text)
        if pos > neg:
            item.sentiment = "positive"
            item.impact_score = min(0.95, 0.55 + pos * 0.08)
        elif neg > pos:
            item.sentiment = "negative"
            item.impact_score = min(0.95, 0.55 + neg * 0.08)
        else:
            item.sentiment = "neutral"
            item.impact_score = 0.5

        if any(k in text for k in _POLICY_KW):
            item.category = "policy"
        elif any(k in text for k in _MARKET_KW):
            item.category = "market"
        elif any(k in text for k in _MACRO_KW):
            item.category = "macro"
        else:
            item.category = "industry"

        item.ai_brief = self._ai_brief(item)
        return item

    def _ai_brief(self, item: EconomicNewsItem) -> str:
        if settings.openai_api_key:
            return self._ai_brief_rules(item) + "（可配置 OPENAI_API_KEY 后接入大模型摘要）"
        return self._ai_brief_rules(item)

    def _ai_brief_rules(self, item: EconomicNewsItem) -> str:
        t = item.title + item.summary
        hints: list[str] = []
        if any(k in t for k in ("降准", "降息", "LPR", "逆回购")):
            hints.append("流动性预期改善，偏利好高 beta 与成长风格")
        if any(k in t for k in ("CPI", "通胀", "PPI")):
            hints.append("关注通胀数据对货币政策与周期板块定价的影响")
        if any(k in t for k in ("PMI", "GDP", "就业")):
            hints.append("宏观基本面信号，或影响指数趋势与顺周期配置")
        if any(k in t for k in ("监管", "处罚", "立案")):
            hints.append("监管事件可能引发相关板块短期波动，注意个股风险")
        if any(k in t for k in ("北向", "外资", "美联储")):
            hints.append("外部流动性与风险偏好变化，关注北向与汇率联动")
        if not hints:
            cat_map = {
                "macro": "宏观信息",
                "policy": "政策动向",
                "market": "市场快讯",
                "industry": "行业动态",
            }
            hints.append(f"{cat_map.get(item.category, '资讯')}，建议结合当前环境与仓位纪律评估影响")
        tone = {"positive": "整体偏正面", "negative": "整体偏负面", "neutral": "中性"}[item.sentiment]
        return f"{tone}：{'；'.join(hints)}。"

    def format_push_message(self, items: list[dict], max_items: int = 8) -> str:
        lines = ["【量化 V5.1 · 经济/财经新闻推送】"]
        for it in items[:max_items]:
            tag = {"macro": "宏观", "policy": "政策", "market": "市场", "industry": "行业"}.get(
                it.get("category", ""), "资讯"
            )
            lines.append(f"• [{tag}] {it.get('title', '')}")
            brief = it.get("ai_brief") or it.get("summary", "")
            if brief:
                lines.append(f"  ↳ {brief[:120]}")
        lines.append("\n— 来自 QTS 经济新闻模块，仅供参考")
        return "\n".join(lines)

    def mark_pushed(self, ids: list[str]) -> None:
        data = self.load()
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        id_set = set(ids)
        for row in data.get("items", []):
            if row.get("id") in id_set:
                row["pushed_at"] = now
        data["updated_at"] = data.get("updated_at")
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _dedupe(self, items: list[EconomicNewsItem]) -> list[EconomicNewsItem]:
        seen: set[str] = set()
        out: list[EconomicNewsItem] = []
        for it in items:
            key = re.sub(r"\s+", "", it.title)[:80]
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    def _fallback_items(self) -> list[EconomicNewsItem]:
        now = datetime.now(timezone.utc).astimezone()
        samples = [
            ("央行公开市场操作维持流动性合理充裕", "macro"),
            ("制造业 PMI 公布，关注景气度与顺周期板块", "macro"),
            ("监管层就资本市场改革发声，强调稳定预期", "policy"),
            ("北向资金净流入，消费与金融板块获青睐", "market"),
        ]
        out: list[EconomicNewsItem] = []
        for i, (title, cat) in enumerate(samples):
            ts = (now - timedelta(minutes=15 * i)).isoformat(timespec="seconds")
            out.append(
                EconomicNewsItem(
                    id=hashlib.md5(title.encode()).hexdigest()[:16],
                    title=title,
                    summary=title + "（示例数据：外网 RSS 不可用时展示，可点击刷新拉取真实源）",
                    source="QTS 本地",
                    published_at=ts,
                    url="",
                    category=cat,
                )
            )
        return out

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text or "").replace("&nbsp;", " ").strip()

    @staticmethod
    def _hostname(url: str) -> str:
        m = re.match(r"https?://([^/]+)", url)
        return m.group(1) if m else "RSS"

    @staticmethod
    def _text(node: ET.Element, tag: str) -> str:
        el = node.find(tag)
        if el is not None and el.text:
            return el.text
        el = node.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
        return (el.text or "").strip() if el is not None else ""

    @staticmethod
    def _link(node: ET.Element) -> str:
        link = node.find("link")
        if link is not None:
            href = link.get("href") or (link.text or "")
            if href:
                return href.strip()
        el = node.find("link")
        if el is not None and el.text:
            return el.text.strip()
        guid = node.find("guid")
        if guid is not None and guid.text:
            return guid.text.strip()
        return ""

    @staticmethod
    def _parse_time(raw: str) -> str:
        if not raw:
            return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        try:
            return parsedate_to_datetime(raw).astimezone().isoformat(timespec="seconds")
        except Exception:
            pass
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone().isoformat(timespec="seconds")
        except Exception:
            return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
