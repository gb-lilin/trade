from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from app.core.types import Bar, Quote
from app.data.base import DataSource
from app.data.market import MarketDataService
from app.data.regime import RegimeDetector
from app.data.sector import SectorService
from app.data.akshare_src import AkshareDataSource
from app.data.tencent import TencentDataSource
from app.data.tushare_src import TuShareSource


class DataManager:
    def __init__(self) -> None:
        self._sources: list[DataSource] = [AkshareDataSource(), TencentDataSource()]
        self.market = MarketDataService()
        self.regime = RegimeDetector()
        self.sector = SectorService()
        self.tushare = TuShareSource()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = 30.0

    async def get_quote(self, symbol: str, retries: int = 2) -> Quote | None:
        for attempt in range(retries + 1):
            for src in self._sources:
                q = await src.get_quote(symbol)
                if q and q.price > 0:
                    return q
            if attempt < retries:
                await asyncio.sleep(0.3 * (attempt + 1))
        return None

    async def get_bars(self, symbol: str, limit: int = 120) -> list[Bar]:
        for src in self._sources:
            bars = await src.get_bars(symbol, limit=limit)
            if bars:
                return bars
        return []

    async def get_regime(self, *, force_market_refresh: bool = False) -> dict:
        snap = await self.market.get_snapshot(force_refresh=force_market_refresh)
        adv = snap.breadth.advancers
        dec = snap.breadth.decliners
        ratio = adv / max(adv + dec, 1)
        flow = await self.tushare.northbound_flow()
        m = self.regime.analyze(advance_ratio=ratio, northbound_flow=flow)
        return {
            "regime": m.regime.value,
            "environment_multiplier": m.environment_multiplier,
            "metrics": {
                "trend": m.trend_score,
                "breadth": m.breadth_score,
                "volatility": m.volatility_score,
                "flow": m.flow_score,
            },
        }


@lru_cache
def get_data_manager() -> DataManager:
    return DataManager()
