#!/usr/bin/env python3
"""盘前选股扫描（建议 9:25 定时任务）。"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.deps import get_services  # noqa: E402


async def main() -> None:
    s = get_services()
    picks = await s["screener"].scan()
    for i, p in enumerate(picks[:10], 1):
        print(f"{i}. {p['symbol']} | {p['strategy']} | score={p['composite_score']}")


if __name__ == "__main__":
    asyncio.run(main())
