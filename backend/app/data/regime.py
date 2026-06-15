from __future__ import annotations

from dataclasses import dataclass

from app.core.types import MarketRegime


@dataclass
class RegimeMetrics:
    trend_score: float
    breadth_score: float
    volatility_score: float
    flow_score: float
    regime: MarketRegime
    environment_multiplier: float


class RegimeDetector:
    def analyze(
        self,
        index_change_pct: float = 0.0,
        advance_ratio: float = 0.5,
        atr_pct: float = 2.0,
        northbound_flow: float = 0.0,
    ) -> RegimeMetrics:
        trend = max(-1.0, min(1.0, index_change_pct / 3.0))
        breadth = (advance_ratio - 0.5) * 2
        vol = max(0.0, min(1.0, atr_pct / 5.0))
        flow = max(-1.0, min(1.0, northbound_flow / 50.0))

        score = trend * 0.35 + breadth * 0.25 + flow * 0.25 - vol * 0.15
        if score > 0.35:
            regime = MarketRegime.BULL
            mult = 1.1
        elif score < -0.35:
            regime = MarketRegime.BEAR
            mult = 0.6
        elif vol > 0.6:
            regime = MarketRegime.HIGH_VOL
            mult = 0.75
        else:
            regime = MarketRegime.NEUTRAL
            mult = 0.9

        return RegimeMetrics(
            trend_score=round(trend, 3),
            breadth_score=round(breadth, 3),
            volatility_score=round(vol, 3),
            flow_score=round(flow, 3),
            regime=regime,
            environment_multiplier=mult,
        )
