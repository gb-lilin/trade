from __future__ import annotations

import asyncio

from app.data.eastmoney_market import fetch_market_live


class SectorService:
    async def hot_sectors(self, limit: int = 10) -> list[dict]:
        try:
            live = await asyncio.to_thread(fetch_market_live, sector_limit=limit)
            return list(live.get("hot_sectors") or [])[:limit]
        except Exception:
            return []
