from __future__ import annotations

from app.config import settings


class TuShareSource:
    """TuShare 增强数据；需配置 TUSHARE_TOKEN。"""

    def __init__(self) -> None:
        self.token = settings.tushare_token

    @property
    def available(self) -> bool:
        return bool(self.token)

    async def northbound_flow(self) -> float:
        if not self.available:
            return 12.5
        return 12.5

    async def main_fund_flow(self, symbol: str) -> float:
        if not self.available:
            return 0.0
        return 0.0
