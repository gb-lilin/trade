from __future__ import annotations

import math
from typing import Sequence


def sma(series: Sequence[float], window: int) -> float:
    chunk = list(series)[-window:]
    if not chunk:
        return 0.0
    return sum(chunk) / len(chunk)


def ema(series: Sequence[float], window: int) -> float:
    vals = list(series)
    if not vals:
        return 0.0
    k = 2 / (window + 1)
    e = vals[0]
    for v in vals[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(closes: Sequence[float], period: int = 14) -> float:
    vals = list(closes)
    if len(vals) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(-period, 0):
        d = vals[i] - vals[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(closes: Sequence[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float, float, float]:
    vals = list(closes)
    if len(vals) < slow:
        return 0.0, 0.0, 0.0
    line_series: list[float] = []
    for i in range(len(vals)):
        sub = vals[: i + 1]
        line_series.append(ema(sub, fast) - ema(sub, slow))
    line = line_series[-1]
    sig = ema(line_series, signal)
    return line, sig, line - sig


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    h, l, c = list(highs), list(lows), list(closes)
    if len(c) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        trs.append(tr)
    window = trs[-period:]
    return sum(window) / len(window) if window else 0.0


def quantile_rank(value: float, history: Sequence[float]) -> float:
    if not history:
        return 0.5
    return sum(1 for x in history if x <= value) / len(history)


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b == 0 or math.isnan(b):
        return default
    return a / b
