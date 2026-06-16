from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.monitor.news_sources import RSS_LABEL_BY_HOST, RawNewsItem, fetch_all_sources, fetch_rss


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
    sources: list[str] = field(default_factory=list)
    consensus: int = 1
    is_recent: bool = False
    macro_policy: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_RSS = [
    "https://feedx.net/rss/cls.xml",
    "https://feedx.net/rss/wallstreetcn.xml",
]  # 内置源见 news_sources.LABELED_RSS_FEEDS；此处仅供 .env 示例引用

_SOURCE_PRIORITY = (
    "央视新闻",
    "华尔街日报",
    "东方财富网",
    "财联社",
    "华尔街见闻",
    "新浪财经",
    "中国新闻网",
    "人民网",
)

_POS_KW = ("增长", "复苏", "利好", "上调", "超预期", "降准", "降息", "刺激", "回暖")
_NEG_KW = ("下滑", "衰退", "利空", "下调", "不及预期", "制裁", "违约", "暴跌", "收紧")
_MACRO_KW = ("GDP", "CPI", "PPI", "PMI", "央行", "国务院", "财政部", "美联储", "通胀", "就业")
_POLICY_KW = ("政策", "监管", "条例", "会议", "规划", "试点")
_MARKET_KW = ("A股", "沪深", "指数", "北向", "融资", "成交量", "涨停", "跌停")
_MACRO_POLICY_EXTRA = (
    "宏观",
    "货币政策",
    "财政政策",
    "国务院",
    "证监会",
    "发改委",
    "央行",
    "降准",
    "降息",
    "LPR",
    "专项债",
    "国债",
    "汇率",
    "关税",
    "美联储",
    "Fed ",
    "Federal Reserve",
    "White House",
    "Treasury",
    "ECB",
    "BOJ",
)


class EconomicNewsService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or Path(__file__).resolve().parents[2] / "data" / "economic_news.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_fetch_stats: dict[str, Any] = {}

    def _rss_urls(self) -> list[str]:
        raw = settings.news_rss_urls.strip()
        if not raw:
            return []
        return [u.strip() for u in raw.split(",") if u.strip()]

    def last_fetch_stats(self) -> dict[str, Any]:
        return dict(self._last_fetch_stats)

    def load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"updated_at": None, "items": []}
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def save(self, items: list[EconomicNewsItem], *, fetch_stats: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "items": [i.to_dict() for i in items],
        }
        if fetch_stats:
            payload["fetch_stats"] = fetch_stats
        self.store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def list_items(self, limit: int = 30) -> dict[str, Any]:
        data = self.load()
        items = self._filter_item_dicts(data.get("items", []))[:limit]
        return {
            "updated_at": data.get("updated_at"),
            "items": items,
            "count": len(items),
            "fetch_stats": data.get("fetch_stats"),
            "filter": self._filter_meta(),
        }

    async def refresh(self, limit_per_feed: int = 15) -> dict[str, Any]:
        collected: list[EconomicNewsItem] = []
        fetch_stats: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            raw_items, fetch_stats = await fetch_all_sources(client, limit_per_source=limit_per_feed)
            for url in self._rss_urls():
                try:
                    host = self._hostname(url)
                    label = RSS_LABEL_BY_HOST.get(host, host)
                    extra = await fetch_rss(client, url, label, limit_per_feed, timeout=8.0)
                    raw_items.extend(extra)
                    fetch_stats.setdefault("ok", []).append(f"自定义:{label}")
                    fetch_stats.setdefault("counts", {})[f"自定义:{label}"] = len(extra)
                except Exception as exc:
                    fetch_stats.setdefault("failed", []).append(
                        {"source": f"自定义:{url}", "error": str(exc)[:120]}
                    )
            collected = [self._from_raw(x) for x in raw_items]

        if not collected:
            collected = self._fallback_items()
            fetch_stats = {"ok": [], "failed": [{"source": "全部源", "error": "采集失败，使用本地示例"}], "counts": {}}
        else:
            collected = self._dedupe(self._merge_cross_source(collected))

        self._last_fetch_stats = fetch_stats
        all_enriched = [self._enrich_item(x) for x in collected[:80]]
        enriched = self._apply_relevance_filter(all_enriched)
        if not enriched and all_enriched:
            enriched = self._apply_relevance_filter(all_enriched, macro_only=True)
            fetch_stats["filter_note"] = "无 24h 内快讯，已放宽为仅宏观/政策"
        enriched.sort(key=lambda x: (x.is_recent, x.consensus, x.published_at), reverse=True)
        enriched = enriched[:50]
        fetch_stats["filter"] = self._filter_meta(
            kept=len(enriched),
            dropped=max(0, len(all_enriched) - len(enriched)),
        )
        old = {x["id"]: x.get("pushed_at") for x in self.load().get("items", [])}
        for item in enriched:
            if item.id in old and old[item.id]:
                item.pushed_at = old[item.id]
        return self.save(enriched, fetch_stats=fetch_stats)

    def _from_raw(self, raw: RawNewsItem) -> EconomicNewsItem:
        link = raw.url or ""
        nid = hashlib.md5(f"{raw.title}|{link}|{raw.source}".encode()).hexdigest()[:16]
        sources = [raw.source] if raw.source else []
        return EconomicNewsItem(
            id=nid,
            title=raw.title.strip(),
            summary=(raw.summary or raw.title).strip(),
            source=raw.source,
            published_at=raw.published_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            url=link,
            sources=sources,
            consensus=1,
        )

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

        if item.consensus >= 2:
            item.impact_score = min(0.98, item.impact_score + 0.04 * (item.consensus - 1))

        item.ai_brief = self._ai_brief(item)
        if item.consensus >= 2 and item.sources:
            names = "、".join(item.sources[:4])
            if len(item.sources) > 4:
                names += f" 等{len(item.sources)}家"
            prefix = f"【多方印证·{item.consensus}源】{names}。"
            if not item.ai_brief.startswith("【多方"):
                item.ai_brief = prefix + item.ai_brief
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
        hours = int(settings.news_fresh_hours)
        lines = [
            "【量化 V5.1 · 经济/财经新闻推送】",
            f"筛选：{hours} 小时内快讯，或宏观/政策要闻 · 多源综合解读",
        ]
        for it in items[:max_items]:
            tag = {"macro": "宏观", "policy": "政策", "market": "市场", "industry": "行业"}.get(
                it.get("category", ""), "资讯"
            )
            src = it.get("source") or ""
            if it.get("consensus", 1) >= 2:
                src = f"综合({it.get('consensus', 1)}源)"
            lines.append(f"• [{tag}] {it.get('title', '')}" + (f"（{src}）" if src else ""))
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
            key = self._title_key(it.title)
            if key in seen:
                continue
            seen.add(key)
            out.append(it)
        return out

    def _merge_cross_source(self, items: list[EconomicNewsItem]) -> list[EconomicNewsItem]:
        """相近标题合并为一条，汇总媒体来源与综合解读权重。"""
        groups: list[list[EconomicNewsItem]] = []
        for it in items:
            placed = False
            for group in groups:
                if any(self._titles_related(it.title, g.title) for g in group):
                    group.append(it)
                    placed = True
                    break
            if not placed:
                groups.append([it])

        merged: list[EconomicNewsItem] = []
        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
                continue
            merged.append(self._merge_group(group))
        return merged

    def _merge_group(self, group: list[EconomicNewsItem]) -> EconomicNewsItem:
        group.sort(key=lambda x: self._source_rank(x.source))
        primary = group[0]
        sources: list[str] = []
        for g in group:
            for s in g.sources or [g.source]:
                if s and s not in sources:
                    sources.append(s)
        summaries = [g.summary for g in group if g.summary and g.summary != g.title]
        summary = max(summaries, key=len) if summaries else primary.summary
        primary.sources = sources
        primary.consensus = len(sources)
        primary.source = self._format_composite_source(sources)
        primary.summary = summary[:400]
        primary.id = hashlib.md5(f"{primary.title}|{'|'.join(sources)}".encode()).hexdigest()[:16]
        primary.published_at = max(g.published_at for g in group)
        if not primary.url:
            for g in group:
                if g.url:
                    primary.url = g.url
                    break
        return primary

    @staticmethod
    def _format_composite_source(sources: list[str]) -> str:
        if len(sources) <= 1:
            return sources[0] if sources else "综合"
        shown = "、".join(sources[:3])
        if len(sources) > 3:
            shown += f" 等{len(sources)}家"
        return f"综合·{shown}"

    @staticmethod
    def _source_rank(label: str) -> int:
        try:
            return _SOURCE_PRIORITY.index(label)
        except ValueError:
            return len(_SOURCE_PRIORITY)

    @staticmethod
    def _title_key(title: str) -> str:
        t = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", title or "")
        return t[:80]

    @classmethod
    def _titles_related(cls, a: str, b: str) -> bool:
        ka, kb = cls._title_key(a), cls._title_key(b)
        if not ka or not kb:
            return False
        if ka == kb:
            return True
        short, long = (ka, kb) if len(ka) <= len(kb) else (kb, ka)
        if len(short) >= 10 and short in long:
            return True
        if len(long) >= 10 and long in short:
            return True

        def bigrams(s: str) -> set[str]:
            return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set()

        ba, bb = bigrams(ka), bigrams(kb)
        if not ba or not bb:
            return False
        jaccard = len(ba & bb) / len(ba | bb)
        return jaccard >= 0.55 and min(len(ka), len(kb)) >= 12

    def _fallback_items(self) -> list[EconomicNewsItem]:
        now = datetime.now(timezone.utc).astimezone()
        samples = [
            ("央行公开市场操作维持流动性合理充裕", "macro"),
            ("制造业 PMI 公布，关注景气度与顺周期板块", "macro"),
            ("监管层就资本市场改革发声，强调稳定预期", "policy"),
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
    def _hostname(url: str) -> str:
        m = re.match(r"https?://([^/]+)", url)
        return m.group(1) if m else "RSS"

    def _filter_meta(self, *, kept: int | None = None, dropped: int | None = None) -> dict[str, Any]:
        hours = settings.news_fresh_hours
        meta: dict[str, Any] = {
            "fresh_hours": hours,
            "rule": f"{int(hours)} 小时内快讯，或宏观/政策类",
        }
        if kept is not None:
            meta["kept"] = kept
        if dropped is not None:
            meta["dropped"] = dropped
        return meta

    def _parse_published_at(self, raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone()
        except ValueError:
            return None

    def _is_recent(self, item: EconomicNewsItem) -> bool:
        dt = self._parse_published_at(item.published_at)
        if dt is None:
            return False
        now = datetime.now(timezone.utc).astimezone()
        return (now - dt) <= timedelta(hours=settings.news_fresh_hours)

    def _is_macro_policy(self, item: EconomicNewsItem) -> bool:
        if item.category in ("macro", "policy"):
            return True
        text = f"{item.title} {item.summary}"
        keys = _MACRO_KW + _POLICY_KW + _MACRO_POLICY_EXTRA
        return any(k in text for k in keys)

    def _apply_relevance_filter(
        self, items: list[EconomicNewsItem], *, macro_only: bool = False
    ) -> list[EconomicNewsItem]:
        out: list[EconomicNewsItem] = []
        for item in items:
            item.is_recent = self._is_recent(item)
            item.macro_policy = self._is_macro_policy(item)
            if macro_only:
                if item.macro_policy:
                    out.append(item)
            elif item.is_recent or item.macro_policy:
                out.append(item)
        return out

    def _filter_item_dicts(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        items = [self._item_from_dict(r) for r in rows]
        items = [self._enrich_item(x) for x in items]
        filtered = self._apply_relevance_filter(items)
        return [x.to_dict() for x in filtered]

    @staticmethod
    def _item_from_dict(row: dict[str, Any]) -> EconomicNewsItem:
        return EconomicNewsItem(
            id=str(row.get("id", "")),
            title=str(row.get("title", "")),
            summary=str(row.get("summary", "")),
            source=str(row.get("source", "")),
            published_at=str(row.get("published_at", "")),
            url=str(row.get("url", "")),
            category=str(row.get("category", "macro")),
            sentiment=str(row.get("sentiment", "neutral")),
            impact_score=float(row.get("impact_score", 0.5)),
            ai_brief=str(row.get("ai_brief", "")),
            pushed_at=row.get("pushed_at"),
            sources=list(row.get("sources") or []),
            consensus=int(row.get("consensus", 1)),
        )
