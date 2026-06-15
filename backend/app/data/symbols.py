from __future__ import annotations

"""A 股代码 → 简称（行情不可用时兜底）。"""

KNOWN_STOCK_NAMES: dict[str, str] = {
    "600519": "贵州茅台",
    "000858": "五粮液",
    "300750": "宁德时代",
    "688981": "中芯国际",
    "002230": "科大讯飞",
    "601318": "中国平安",
    "000001": "平安银行",
    "600036": "招商银行",
    "000333": "美的集团",
    "601888": "中国中免",
    "510300": "沪深300ETF",
    "510500": "中证500ETF",
    "512100": "中证1000ETF",
    "159915": "创业板ETF",
    "588000": "科创50ETF",
    "512880": "证券ETF",
    "512690": "酒ETF",
    "515790": "光伏ETF",
    "512890": "红利低波ETF",
    "518880": "黄金ETF",
    "513100": "纳指ETF",
    "159920": "恒生ETF",
    "511260": "十年国债ETF",
}


def normalize_symbol(symbol: str) -> str:
    s = symbol.upper().strip()
    if s.startswith("SH") and len(s) > 2:
        return s[2:]
    if s.startswith("SZ") and len(s) > 2:
        return s[2:]
    return s.replace(".SH", "").replace(".SZ", "")


def tencent_quote_code(symbol: str) -> str:
    """腾讯行情接口代码：sh600519 / sz159915。"""
    s = normalize_symbol(symbol)
    if s.startswith("159") or s.startswith(("000", "001", "002", "003", "300", "301")):
        return f"sz{s}"
    if s.startswith(("600", "601", "603", "605", "688", "689")):
        return f"sh{s}"
    # 上证 ETF / 场内基金（51、58 等）
    if s.startswith(("51", "58")):
        return f"sh{s}"
    if s.startswith("6"):
        return f"sh{s}"
    return f"sz{s}"


def display_name(symbol: str, from_quote: str | None = None) -> str:
    norm = normalize_symbol(symbol)
    if from_quote:
        qn = from_quote.strip()
        if qn and qn != norm and not (qn.isdigit() and len(qn) <= 6):
            return qn
    return KNOWN_STOCK_NAMES.get(norm, from_quote.strip() if from_quote else norm)
