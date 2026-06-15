from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

import httpx

from app.core.types import Bar, Quote
from app.data.base import DataSource
from app.data.symbols import display_name, tencent_quote_code


class TencentDataSource(DataSource):
    name = "tencent"

    async def get_quote(self, symbol: str) -> Quote | None:
        code = tencent_quote_code(symbol)
        url = f"https://qt.gtimg.cn/q={code}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return self._mock_quote(symbol)
                text = r.text
                if "none_match" in text or "pv_none" in text:
                    return self._mock_quote(symbol)
                parts = text.split("~")
                if len(parts) < 5:
                    return self._mock_quote(symbol)
                price = float(parts[3] or 0)
                if price <= 0:
                    return self._mock_quote(symbol)
                raw_name = parts[1] if len(parts) > 1 else ""
                name = display_name(symbol, raw_name or None)
                prev_close = float(parts[4] or 0) if len(parts) > 4 and parts[4] else 0.0
                change_pct = self._parse_change_pct(parts, price, prev_close)
                vol = float(parts[36]) if len(parts) > 36 and parts[36] else 0.0
                return Quote(symbol=symbol, name=name, price=price, change_pct=change_pct, volume=vol)
        except Exception:
            return self._mock_quote(symbol)

    def _parse_change_pct(self, parts: list[str], price: float, prev_close: float) -> float:
        parsed = 0.0
        if len(parts) > 32 and parts[32]:
            try:
                parsed = float(parts[32])
            except ValueError:
                parsed = 0.0
        if prev_close > 0:
            calc = round((price - prev_close) / prev_close * 100, 2)
            if len(parts) <= 32 or not parts[32]:
                return calc
            if abs(parsed - calc) > 0.2:
                return calc
            return round(parsed, 2)
        return round(parsed, 2)

    async def get_bars(self, symbol: str, limit: int = 120) -> list[Bar]:
        q = await self.get_quote(symbol)
        base = q.price if q and q.price > 0 else 10.0
        bars: list[Bar] = []
        dt = datetime.now()
        price = base
        for i in range(limit):
            d = (dt - timedelta(days=limit - i)).strftime("%Y-%m-%d")
            o = price * (1 + random.uniform(-0.02, 0.02))
            c = o * (1 + random.uniform(-0.03, 0.03))
            h = max(o, c) * (1 + random.uniform(0, 0.02))
            l = min(o, c) * (1 - random.uniform(0, 0.02))
            v = random.uniform(1e6, 5e7)
            bars.append(Bar(symbol=symbol, date=d, open=o, high=h, low=l, close=c, volume=v))
            price = c
        return bars

    def _mock_quote(self, symbol: str) -> Quote:
        p = random.uniform(8, 80)
        return Quote(
            symbol=symbol,
            name=display_name(symbol),
            price=round(p, 2),
            change_pct=round(random.uniform(-5, 5), 2),
        )
