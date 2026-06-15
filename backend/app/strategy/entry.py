from __future__ import annotations

from app.core.types import SignalSide, StrategyKind, TradeIntent


class EntryEngine:
    """V5 双策略买卖决策。"""

    buy_threshold = 0.58
    sell_threshold = 0.42

    def decide(
        self,
        symbol: str,
        composite_score: float,
        strategy: StrategyKind,
        has_position: bool,
        emotion: float,
    ) -> TradeIntent | None:
        adj = composite_score
        if strategy == StrategyKind.OVERSOLD_REBOUND and emotion < 35:
            adj += 0.05
        if strategy == StrategyKind.LIMIT_UP_DRAGON and emotion > 70:
            adj -= 0.08

        if not has_position and adj >= self.buy_threshold:
            return TradeIntent(
                symbol=symbol,
                side=SignalSide.BUY,
                strategy=strategy,
                score=adj,
                reason=f"综合分 {adj:.2f} 达买入阈值",
                suggested_weight=min(0.2, (adj - 0.5) * 0.8),
            )
        if has_position and adj <= self.sell_threshold:
            return TradeIntent(
                symbol=symbol,
                side=SignalSide.SELL,
                strategy=strategy,
                score=adj,
                reason=f"综合分 {adj:.2f} 达卖出阈值",
            )
        return None
