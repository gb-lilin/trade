from __future__ import annotations

from app.core import utils
from app.core.types import Bar, FactorSnapshot


FACTOR_GROUPS = {
    "momentum": ["rsi_14", "macd_hist", "roc_5"],
    "trend": ["sma_20_bias", "ema_12_bias"],
    "volatility": ["atr_pct", "range_pct"],
    "volume": ["vol_ratio"],
    "reversal": ["oversold_score"],
    "strength": ["limit_strength"],
}


class FactorEngine:
    def compute(self, symbol: str, bars: list[Bar], limit_up: bool = False) -> FactorSnapshot:
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        vols = [b.volume for b in bars]

        factors: dict[str, float] = {}
        if len(closes) >= 15:
            factors["rsi_14"] = utils.rsi(closes) / 100.0
            _, _, hist = utils.macd(closes)
            factors["macd_hist"] = max(-1.0, min(1.0, hist / (closes[-1] * 0.01 + 1e-9)))
            factors["roc_5"] = (closes[-1] - closes[-6]) / closes[-6] if len(closes) > 6 else 0
            sma20 = utils.sma(closes, 20)
            factors["sma_20_bias"] = (closes[-1] - sma20) / sma20 if sma20 else 0
            ema12 = utils.ema(closes, 12)
            factors["ema_12_bias"] = (closes[-1] - ema12) / ema12 if ema12 else 0
            atr_v = utils.atr(highs, lows, closes)
            factors["atr_pct"] = atr_v / closes[-1] if closes[-1] else 0
            factors["range_pct"] = (highs[-1] - lows[-1]) / closes[-1] if closes[-1] else 0
            avg_vol = utils.sma(vols, 20) or 1
            factors["vol_ratio"] = min(3.0, vols[-1] / avg_vol) / 3.0
            factors["oversold_score"] = max(0.0, (30 - utils.rsi(closes)) / 30.0)
        limit_str = 1.0 if limit_up else 0.0
        if len(closes) >= 2 and limit_str < 0.5:
            day_chg = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] else 0.0
            if day_chg >= 0.095:
                limit_str = min(1.0, day_chg / 0.10)
        factors["limit_strength"] = limit_str

        return FactorSnapshot(symbol=symbol, factors=factors, composite_score=0.0)
