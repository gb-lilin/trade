#!/usr/bin/env python3
"""AI/规则驱动的经济财经新闻推送（可定时任务 + 飞书）。"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.deps import get_services  # noqa: E402


async def main() -> None:
    s = get_services()
    result = await s["ai_news"].refresh_and_push(max_items=8)
    print(result.get("preview", ""))
    print(f"\nfeishu_pushed={result.get('pushed_to_feishu')}")


if __name__ == "__main__":
    asyncio.run(main())
