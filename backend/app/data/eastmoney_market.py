from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx

from app.data.akshare_src import _EM_HEADERS, _to_float, akshare_available

# 部分网络环境 push2 会被断开，push2delay 通常可用（与 AKShare 备用节点一致）
_EM_API_BASES = (
    "https://push2delay.eastmoney.com",
    "https://push2.eastmoney.com",
)
_UT = "bd1d9ddb04089700cf9c27f6f7426281"
_A_SHARE_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
_INDUSTRY_BOARD_FS = "m:90+t:2"
_CN_TZ = timezone(timedelta(hours=8))


def _shanghai_today() -> str:
    return datetime.now(_CN_TZ).date().isoformat()


def _shanghai_now_iso() -> str:
    return datetime.now(_CN_TZ).isoformat(timespec="seconds")


def _is_missing_quote(value: object) -> bool:
    s = str(value or "").strip()
    return not s or s in {"-", "--"}


def _row_change_pct(row: object) -> float | None:
    if isinstance(row, dict):
        raw = row.get("f3")
    elif isinstance(row, (list, tuple)) and row:
        raw = row[-1]
    else:
        return None
    if _is_missing_quote(raw):
        return None
    return _to_float(raw)


def _row_code(row: object) -> str:
    if isinstance(row, dict):
        return str(row.get("f12") or "").zfill(6)
    return ""


def _is_limit_up(code: str, change_pct: float) -> bool:
    if change_pct <= 0:
        return False
    if code.startswith(("688", "300", "301")):
        return change_pct >= 19.5
    if code.startswith(("8", "4")):
        return change_pct >= 29.5
    return change_pct >= 9.5


def _is_limit_down(code: str, change_pct: float) -> bool:
    if change_pct >= 0:
        return False
    if code.startswith(("688", "300", "301")):
        return change_pct <= -19.5
    if code.startswith(("8", "4")):
        return change_pct <= -29.5
    return change_pct <= -9.5


def _http_get_clist(
    client: httpx.Client,
    *,
    fs: str,
    fields: str,
    pn: int,
    pz: int,
    fid: str = "f3",
    po: int = 1,
) -> dict:
    params = {
        "pn": pn,
        "pz": pz,
        "po": po,
        "np": 1,
        "ut": _UT,
        "fltt": 2,
        "invt": 2,
        "fid": fid,
        "fs": fs,
        "fields": fields,
    }
    last_err: Exception | None = None
    for base in _EM_API_BASES:
        url = f"{base}/api/qt/clist/get"
        try:
            r = client.get(url, params=params)
            r.raise_for_status()
            body = r.json()
            data = body.get("data")
            if data is not None:
                return data
            if body.get("rc") not in (None, 0):
                last_err = RuntimeError(str(body.get("rt") or "eastmoney clist error"))
        except Exception as exc:
            last_err = exc
    raise last_err or RuntimeError("eastmoney clist failed")


def _empty_breadth() -> dict[str, int]:
    return {
        "advancers": 0,
        "decliners": 0,
        "flat": 0,
        "limit_up": 0,
        "limit_down": 0,
        "oversold_count": 0,
    }


def _fetch_breadth_httpx() -> dict[str, int]:
    advancers = decliners = flat = limit_up = limit_down = oversold_count = 0
    valid_quotes = 0
    fields = "f12,f3"
    pz = 500
    pn = 1
    total = 0
    with httpx.Client(timeout=25.0, headers=_EM_HEADERS) as client:
        while pn <= 15:
            data = _http_get_clist(client, fs=_A_SHARE_FS, fields=fields, pn=pn, pz=pz)
            diff = data.get("diff") or []
            if not diff:
                break
            total = int(data.get("total") or total)
            for row in diff:
                ch = _row_change_pct(row)
                if ch is None:
                    continue
                valid_quotes += 1
                code = _row_code(row)
                if ch > 0:
                    advancers += 1
                elif ch < 0:
                    decliners += 1
                else:
                    flat += 1
                if _is_limit_up(code, ch):
                    limit_up += 1
                elif _is_limit_down(code, ch):
                    limit_down += 1
                if ch <= -5.0:
                    oversold_count += 1
            if pn * pz >= total:
                break
            pn += 1
            time.sleep(0.08)
    if valid_quotes > 0:
        return {
            "advancers": advancers,
            "decliners": decliners,
            "flat": flat,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "oversold_count": oversold_count,
        }
    if total > 0:
        # 盘外/休市：个股涨跌幅字段常为 "-"，仍返回成功以便展示板块等信息
        return _empty_breadth()
    raise RuntimeError("empty a-share breadth")


def _fetch_hot_sectors_httpx(limit: int = 8) -> list[dict]:
    with httpx.Client(timeout=20.0, headers=_EM_HEADERS) as client:
        data = _http_get_clist(
            client,
            fs=_INDUSTRY_BOARD_FS,
            fields="f12,f14,f3",
            pn=1,
            pz=max(limit * 3, 24),
            fid="f3",
            po=1,
        )
    diff = data.get("diff") or []
    out: list[dict] = []
    for row in diff:
        if not isinstance(row, dict):
            continue
        name = str(row.get("f14") or "").strip()
        if not name:
            continue
        out.append(
            {
                "code": str(row.get("f12") or ""),
                "name": name,
                "change_pct": round(_to_float(row.get("f3")), 2),
            }
        )
    out.sort(key=lambda x: x["change_pct"], reverse=True)
    out = out[:limit]
    if not out:
        raise RuntimeError("empty hot sectors")
    return out


def _fetch_breadth_akshare() -> dict[str, int] | None:
    if not akshare_available():
        return None
    import akshare as ak  # type: ignore[import-untyped]

    try:
        df = ak.stock_zh_a_spot_em()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    code_col = "代码" if "代码" in df.columns else None
    pct_col = "涨跌幅" if "涨跌幅" in df.columns else None
    if not code_col or not pct_col:
        return None
    advancers = decliners = flat = limit_up = limit_down = oversold_count = 0
    for _, row in df.iterrows():
        code = str(row[code_col]).zfill(6)
        ch = _to_float(row[pct_col])
        if ch > 0:
            advancers += 1
        elif ch < 0:
            decliners += 1
        else:
            flat += 1
        if _is_limit_up(code, ch):
            limit_up += 1
        elif _is_limit_down(code, ch):
            limit_down += 1
        if ch <= -5.0:
            oversold_count += 1
    return {
        "advancers": advancers,
        "decliners": decliners,
        "flat": flat,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "oversold_count": oversold_count,
    }


def _fetch_hot_sectors_akshare(limit: int = 8) -> list[dict] | None:
    if not akshare_available():
        return None
    import akshare as ak  # type: ignore[import-untyped]

    try:
        df = ak.stock_board_industry_name_em()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    name_col = "板块名称" if "板块名称" in df.columns else None
    pct_col = "涨跌幅" if "涨跌幅" in df.columns else None
    code_col = "板块代码" if "板块代码" in df.columns else None
    if not name_col or not pct_col:
        return None
    df = df.sort_values(by=pct_col, ascending=False)
    out: list[dict] = []
    for _, row in df.head(limit).iterrows():
        out.append(
            {
                "code": str(row[code_col]) if code_col else "",
                "name": str(row[name_col]),
                "change_pct": round(_to_float(row[pct_col]), 2),
            }
        )
    return out or None


def fetch_market_live(*, sector_limit: int = 8, retries: int = 2) -> dict:
    """拉取 A 股市场宽度与行业热门板块（当日/最新行情）。"""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        breadth: dict[str, int] | None = None
        sectors: list[dict] | None = None
        source = "eastmoney"
        try:
            breadth = _fetch_breadth_akshare()
            if breadth is not None:
                source = "akshare"
        except Exception:
            breadth = None
        try:
            sectors = _fetch_hot_sectors_akshare(sector_limit)
            if sectors is not None:
                source = "akshare"
        except Exception:
            sectors = None
        try:
            if breadth is None:
                breadth = _fetch_breadth_httpx()
                if source != "akshare":
                    source = "eastmoney"
            if sectors is None:
                sectors = _fetch_hot_sectors_httpx(sector_limit)
                if source != "akshare":
                    source = "eastmoney"
            now = _shanghai_now_iso()
            return {
                "breadth": breadth,
                "hot_sectors": sectors,
                "trade_date": _shanghai_today(),
                "updated_at": now,
                "source": source,
            }
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise last_err or RuntimeError("market fetch failed")
