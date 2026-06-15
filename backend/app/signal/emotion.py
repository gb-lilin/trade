from __future__ import annotations

from app.core import utils
from app.core.types import Bar


class EmotionIndexV2:
    """情绪指数：斜率、分位、ATR 综合。"""

    def compute(self, index_bars: list[Bar]) -> dict:
        closes = [b.close for b in index_bars]
        highs = [b.high for b in index_bars]
        lows = [b.low for b in index_bars]
        if len(closes) < 20:
            return {"emotion": 50.0, "slope": 0.0, "quantile": 0.5, "atr_pct": 0.0}

        slope = (closes[-1] - closes[-10]) / closes[-10] * 100 if closes[-10] else 0
        q = utils.quantile_rank(closes[-1], closes[-60:])
        atr_v = utils.atr(highs, lows, closes)
        atr_pct = atr_v / closes[-1] * 100 if closes[-1] else 0
        emotion = 50 + slope * 3 + (q - 0.5) * 20 - atr_pct * 2
        emotion = max(0.0, min(100.0, emotion))
        return {
            "emotion": round(emotion, 2),
            "slope": round(slope, 3),
            "quantile": round(q, 3),
            "atr_pct": round(atr_pct, 3),
        }
