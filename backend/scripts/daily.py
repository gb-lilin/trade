#!/usr/bin/env python3
"""盘后日报 + 模拟盘汇总（建议 15:05）。"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.deps import get_services  # noqa: E402


async def main() -> None:
    s = get_services()
    dm, paper, screener, feishu = s["dm"], s["paper"], s["screener"], s["feishu"]
    regime = await dm.get_regime()
    picks = await screener.scan()
    snap = paper.snapshot()
    summary = {**snap, "regime": regime["regime"], "picks": picks[:5]}
    text_lines = [
        f"权益 {snap['equity']:,.2f}",
        f"环境 {regime['regime']}",
    ]
    print("\n".join(text_lines))
    await feishu.push_daily(summary)


if __name__ == "__main__":
    asyncio.run(main())
