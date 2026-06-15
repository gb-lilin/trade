from __future__ import annotations

from app.core.types import Bar, FactorSnapshot
from app.data.tushare_src import TuShareSource
from app.signal.factors import FactorEngine


class EnhancedSignal:
    def __init__(self) -> None:
        self.factors = FactorEngine()
        self.tushare = TuShareSource()

    async def enrich(self, symbol: str, bars: list[Bar], base: FactorSnapshot) -> FactorSnapshot:
        if self.tushare.available:
            flow = await self.tushare.main_fund_flow(symbol)
            base.factors["main_fund_flow"] = max(-1.0, min(1.0, flow / 1e8))
        else:
            base.factors["main_fund_flow"] = 0.0
        return base
