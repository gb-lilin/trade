from __future__ import annotations

from app.monitor.feishu import FeishuFormatter, push_feishu


class FeishuPushService:
    def __init__(self) -> None:
        self.formatter = FeishuFormatter()

    async def push_daily(self, summary: dict) -> bool:
        return await push_feishu(self.formatter.daily_report(summary))
