from __future__ import annotations

import httpx

from app.config import settings


class FeishuFormatter:
    def daily_report(self, summary: dict) -> str:
        lines = [
            "【量化 V5.1 日报】",
            f"权益: {summary.get('equity', 0):,.2f}",
            f"现金: {summary.get('cash', 0):,.2f}",
            f"持仓数: {len(summary.get('positions', []))}",
            f"市场环境: {summary.get('regime', 'neutral')}",
        ]
        picks = summary.get("picks", [])[:5]
        if picks:
            lines.append("今日选股 Top5:")
            for p in picks:
                lines.append(f"  {p['symbol']} | {p['strategy']} | 分 {p['composite_score']}")
        return "\n".join(lines)


async def push_feishu(text: str) -> bool:
    if not settings.feishu_webhook:
        return False
    payload = {"msg_type": "text", "content": {"text": text}}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(settings.feishu_webhook, json=payload)
        return r.status_code == 200
