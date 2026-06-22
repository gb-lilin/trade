from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.data.eastmoney_market import fetch_market_live

_CN_TZ = timezone(timedelta(hours=8))


@dataclass
class MarketBreadth:
    advancers: int = 0
    decliners: int = 0
    limit_up: int = 0
    limit_down: int = 0
    oversold_count: int = 0


@dataclass
class MarketSnapshot:
    breadth: MarketBreadth = field(default_factory=MarketBreadth)
    hot_sectors: list[dict] = field(default_factory=list)
    dragon_tiger: list[dict] = field(default_factory=list)
    trade_date: str = ""
    updated_at: str = ""
    source: str = "cache"


class MarketDataService:
    def __init__(self, *, cache_ttl_sec: float = 90.0) -> None:
        self._cache_ttl = cache_ttl_sec
        self._cache: MarketSnapshot | None = None
        self._cache_ts = 0.0
        self._store_path = Path(__file__).resolve().parents[2] / "data" / "market_snapshot.json"
        self._load_persisted()

    def _load_persisted(self) -> None:
        if not self._store_path.exists():
            return
        try:
            raw = json.loads(self._store_path.read_text(encoding="utf-8"))
            self._cache = self._snapshot_from_dict(raw)
            self._cache_ts = time.time()
        except Exception:
            pass

    def _persist(self, snap: MarketSnapshot) -> None:
        payload = {
            "breadth": snap.breadth.__dict__,
            "hot_sectors": snap.hot_sectors,
            "dragon_tiger": snap.dragon_tiger,
            "trade_date": snap.trade_date,
            "updated_at": snap.updated_at,
            "source": snap.source,
        }
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _snapshot_from_dict(raw: dict) -> MarketSnapshot:
        b = raw.get("breadth") or {}
        return MarketSnapshot(
            breadth=MarketBreadth(
                advancers=int(b.get("advancers") or 0),
                decliners=int(b.get("decliners") or 0),
                limit_up=int(b.get("limit_up") or 0),
                limit_down=int(b.get("limit_down") or 0),
                oversold_count=int(b.get("oversold_count") or 0),
            ),
            hot_sectors=list(raw.get("hot_sectors") or []),
            dragon_tiger=list(raw.get("dragon_tiger") or []),
            trade_date=str(raw.get("trade_date") or ""),
            updated_at=str(raw.get("updated_at") or ""),
            source=str(raw.get("source") or "cache"),
        )

    def _fallback_snapshot(self) -> MarketSnapshot:
        if self._cache and self._cache.source not in ("unavailable", ""):
            return self._cache
        self._load_persisted()
        if self._cache and self._cache.source not in ("unavailable", ""):
            return self._cache
        return MarketSnapshot(
            breadth=MarketBreadth(advancers=0, decliners=0, limit_up=0, limit_down=0, oversold_count=0),
            hot_sectors=[],
            dragon_tiger=[],
            trade_date="",
            updated_at="",
            source="unavailable",
        )

    def _apply_live(self, live: dict) -> MarketSnapshot:
        b = live.get("breadth") or {}
        snap = MarketSnapshot(
            breadth=MarketBreadth(
                advancers=int(b.get("advancers") or 0),
                decliners=int(b.get("decliners") or 0),
                limit_up=int(b.get("limit_up") or 0),
                limit_down=int(b.get("limit_down") or 0),
                oversold_count=int(b.get("oversold_count") or 0),
            ),
            hot_sectors=list(live.get("hot_sectors") or []),
            dragon_tiger=[],
            trade_date=str(live.get("trade_date") or ""),
            updated_at=str(live.get("updated_at") or ""),
            source=str(live.get("source") or "live"),
        )
        self._cache = snap
        self._cache_ts = time.time()
        self._persist(snap)
        return snap

    async def get_snapshot(self, *, force_refresh: bool = False) -> MarketSnapshot:
        today = datetime.now(_CN_TZ).date().isoformat()
        if (
            self._cache
            and self._cache.trade_date
            and self._cache.trade_date < today
        ):
            force_refresh = True
        if (
            not force_refresh
            and self._cache
            and (time.time() - self._cache_ts) < self._cache_ttl
        ):
            return self._cache
        try:
            live = await asyncio.to_thread(fetch_market_live)
            return self._apply_live(live)
        except Exception:
            if self._cache and self._cache.source not in ("unavailable", ""):
                return self._cache
            return self._fallback_snapshot()
