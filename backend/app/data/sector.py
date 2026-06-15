from __future__ import annotations


class SectorService:
    async def hot_sectors(self, limit: int = 10) -> list[dict]:
        data = [
            {"code": "BK0447", "name": "半导体", "change_pct": 2.8, "lead_stock": "688981"},
            {"code": "BK0800", "name": "人工智能", "change_pct": 2.1, "lead_stock": "002230"},
            {"code": "BK0493", "name": "锂电池", "change_pct": 1.4, "lead_stock": "300750"},
        ]
        return data[:limit]
