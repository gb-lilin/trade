from __future__ import annotations

from app.monitor.economic_news import EconomicNewsService
from app.monitor.feishu import push_feishu


class AiNewsPushService:
    def __init__(self) -> None:
        self.news = EconomicNewsService()

    async def refresh_and_push(self, max_items: int = 8) -> dict:
        data = await self.news.refresh()
        items = data.get("items", [])[:max_items]
        text = self.news.format_push_message(items, max_items=max_items)
        pushed = await push_feishu(text)
        if pushed:
            self.news.mark_pushed([x["id"] for x in items])
        return {
            "refreshed": len(data.get("items", [])),
            "pushed_to_feishu": pushed,
            "preview": text,
            "items": items,
        }

    async def push_latest(self, max_items: int = 8) -> dict:
        data = self.news.list_items(limit=max_items)
        items = data.get("items", [])
        if not items:
            data = await self.news.refresh()
            items = data.get("items", [])[:max_items]
        text = self.news.format_push_message(items, max_items=max_items)
        pushed = await push_feishu(text)
        if pushed:
            self.news.mark_pushed([x["id"] for x in items])
        return {"pushed_to_feishu": pushed, "preview": text, "items": items}
