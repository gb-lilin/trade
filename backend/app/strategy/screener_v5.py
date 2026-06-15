from __future__ import annotations

from app.core.types import Bar, StrategyKind, TradeIntent, SignalSide
from app.data.manager import DataManager
from app.data.symbols import display_name
from app.signal.composite import CompositeScorer
from app.signal.enhanced import EnhancedSignal
from app.signal.factors import FactorEngine


DEFAULT_UNIVERSE = ["600519", "000858", "300750", "688981", "002230", "601318"]


class ScreenerV5:
    """双策略选股：超跌反弹 + 涨停/龙虎榜。"""

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
        self.factors = FactorEngine()
        self.enhanced = EnhancedSignal()
        self.scorer = CompositeScorer()

    async def scan(self, symbols: list[str] | None = None) -> list[dict]:
        universe = symbols or DEFAULT_UNIVERSE
        results: list[dict] = []
        for sym in universe:
            bars = await self.dm.get_bars(sym, limit=80)
            if not bars:
                continue
            quote = await self.dm.get_quote(sym)
            snap = self.factors.compute(sym, bars)
            snap = await self.enhanced.enrich(sym, bars, snap)
            score = self.scorer.score(snap)
            strategy = self._pick_strategy(snap)
            results.append(
                {
                    "symbol": sym,
                    "name": display_name(sym, quote.name if quote else None),
                    "strategy": strategy.value,
                    "composite_score": score,
                    "factors": snap.factors,
                }
            )
        results.sort(key=lambda x: x["composite_score"], reverse=True)
        return results

    def _pick_strategy(self, snap) -> StrategyKind:
        os_score = snap.factors.get("oversold_score", 0)
        lim = snap.factors.get("limit_strength", 0)
        if lim >= 0.5:
            return StrategyKind.LIMIT_UP_DRAGON
        if os_score >= 0.4:
            return StrategyKind.OVERSOLD_REBOUND
        if lim > os_score:
            return StrategyKind.LIMIT_UP_DRAGON
        return StrategyKind.OVERSOLD_REBOUND
