from __future__ import annotations

from app.core import utils
from app.core.types import Bar


class PositionManager:
    """最终仓位 = 基础 × 环境 × 信号 × ATR 调整。"""

    def final_weight(
        self,
        base_weight: float,
        environment_mult: float,
        signal_score: float,
        bars: list[Bar],
    ) -> float:
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        atr_pct = 0.02
        if len(closes) >= 14:
            atr_v = utils.atr(highs, lows, closes)
            atr_pct = atr_v / closes[-1] if closes[-1] else 0.02
        atr_mult = max(0.5, min(1.2, 0.03 / max(atr_pct, 0.005)))
        signal_mult = 0.7 + signal_score * 0.6
        w = base_weight * environment_mult * signal_mult * atr_mult
        return round(max(0.02, min(0.25, w)), 4)
