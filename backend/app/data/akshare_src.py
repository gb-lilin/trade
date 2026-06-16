from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import httpx

from app.core.types import Bar, Quote
from app.data.base import DataSource
from app.data.symbols import display_name, eastmoney_secid, normalize_symbol

try:
    import akshare as ak  # type: ignore[import-untyped]

    _AKSHARE = ak
except ImportError:  # pragma: no cover - optional dependency
    _AKSHARE = None


def akshare_available() -> bool:
    return _AKSHARE is not None


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    s = str(value).strip().replace(",", "").replace("%", "")
    if not s or s in {"-", "--"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


_EM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}


def _quote_from_bid_ask(symbol: str, code: str) -> Quote | None:
    secid = eastmoney_secid(symbol)
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "fltt": "2",
        "invt": "2",
        "fields": "f43,f57,f58,f169,f170,f47,f60",
        "secid": secid,
    }
    try:
        with httpx.Client(timeout=8.0, headers=_EM_HEADERS) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json().get("data") or {}
    except Exception:
        return None
    price = _to_float(data.get("f43"))
    if price <= 0:
        return None
    raw_name = str(data.get("f58") or data.get("f57") or "")
    name = display_name(symbol, raw_name or None)
    change_pct = _to_float(data.get("f170"))
    if change_pct == 0.0 and data.get("f60"):
        prev = _to_float(data.get("f60"))
        if prev > 0:
            change_pct = round((price - prev) / prev * 100, 2)
    vol = _to_float(data.get("f47"))
    return Quote(symbol=code, name=name, price=price, change_pct=round(change_pct, 2), volume=vol)


def _quote_from_spot_row(symbol: str, code: str) -> Quote | None:
    assert _AKSHARE is not None
    df = _AKSHARE.stock_zh_a_spot_em()
    if df is None or df.empty:
        return None
    code_col = "代码" if "代码" in df.columns else None
    if not code_col:
        return None
    row = df.loc[df[code_col].astype(str).str.zfill(6) == code]
    if row.empty:
        return None
    r = row.iloc[0]
    price = _to_float(r.get("最新价"))
    if price <= 0:
        return None
    name = display_name(symbol, str(r.get("名称") or ""))
    change_pct = _to_float(r.get("涨跌幅"))
    vol = _to_float(r.get("成交量"))
    return Quote(symbol=code, name=name, price=price, change_pct=round(change_pct, 2), volume=vol)


def _quote_from_akshare_bid_ask(symbol: str, code: str) -> Quote | None:
    assert _AKSHARE is not None
    df = _AKSHARE.stock_bid_ask_em(symbol=code)
    if df is None or df.empty or "item" not in df.columns or "value" not in df.columns:
        return None
    mapping = dict(zip(df["item"].astype(str), df["value"]))
    price = _to_float(mapping.get("最新"))
    if price <= 0:
        return None
    change_pct = _to_float(mapping.get("涨幅"))
    vol = _to_float(mapping.get("总手"))
    return Quote(
        symbol=code,
        name=display_name(symbol),
        price=price,
        change_pct=round(change_pct, 2),
        volume=vol,
    )


def _fetch_quote_sync(symbol: str) -> Quote | None:
    code = normalize_symbol(symbol)
    try:
        q = _quote_from_bid_ask(symbol, code)
        if q:
            return q
    except Exception:
        pass
    if _AKSHARE is not None:
        try:
            q = _quote_from_akshare_bid_ask(symbol, code)
            if q:
                return q
        except Exception:
            pass
        try:
            return _quote_from_spot_row(symbol, code)
        except Exception:
            pass
    return None


def _fetch_bars_sync(symbol: str, limit: int) -> list[Bar]:
    if _AKSHARE is None:
        return []
    code = normalize_symbol(symbol)
    end = datetime.now()
    start = end - timedelta(days=max(limit * 2, 60))
    try:
        df = _AKSHARE.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
    except Exception:
        return []
    if df is None or df.empty:
        return []
    bars: list[Bar] = []
    tail = df.tail(limit)
    for _, row in tail.iterrows():
        d = str(row.get("日期", ""))[:10]
        bars.append(
            Bar(
                symbol=code,
                date=d,
                open=_to_float(row.get("开盘")),
                high=_to_float(row.get("最高")),
                low=_to_float(row.get("最低")),
                close=_to_float(row.get("收盘")),
                volume=_to_float(row.get("成交量")),
            )
        )
    return bars


class AkshareDataSource(DataSource):
    """东方财富等公开源，经 AKShare 拉取 A 股实时价与日 K。"""

    name = "akshare"

    async def get_quote(self, symbol: str) -> Quote | None:
        return await asyncio.to_thread(_fetch_quote_sync, symbol)

    async def get_bars(self, symbol: str, limit: int = 120) -> list[Bar]:
        if not akshare_available():
            return []
        return await asyncio.to_thread(_fetch_bars_sync, symbol, limit)
