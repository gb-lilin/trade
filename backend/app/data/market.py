from __future__ import annotations

from dataclasses import dataclass, field

from app.core.types import MarketRegime


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


class MarketDataService:
    async def get_snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            breadth=MarketBreadth(advancers=2456, decliners=1987, limit_up=68, limit_down=12, oversold_count=142),
            hot_sectors=[
                {"name": "半导体", "change_pct": 2.8},
                {"name": "人工智能", "change_pct": 2.1},
                {"name": "新能源", "change_pct": -0.6},
            ],
            dragon_tiger=[
                {"symbol": "600519", "name": "示例龙头", "net_buy": 1.2e8},
            ],
        )
