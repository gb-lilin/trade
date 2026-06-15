from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    NEUTRAL = "neutral"
    HIGH_VOL = "high_vol"


class SignalSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class StrategyKind(str, Enum):
    OVERSOLD_REBOUND = "oversold_rebound"
    LIMIT_UP_DRAGON = "limit_up_dragon"


@dataclass
class Quote:
    symbol: str
    name: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    volume: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Bar:
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class FactorSnapshot:
    symbol: str
    factors: dict[str, float] = field(default_factory=dict)
    composite_score: float = 0.0


@dataclass
class TradeIntent:
    symbol: str
    side: SignalSide
    strategy: StrategyKind
    score: float
    reason: str
    suggested_weight: float = 0.0


@dataclass
class Position:
    symbol: str
    name: str
    shares: int
    avg_cost: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def pnl_pct(self) -> float:
        if self.avg_cost <= 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100


@dataclass
class BacktestResult:
    total_return_pct: float
    max_drawdown_pct: float
    sharpe: float
    trades: int
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
