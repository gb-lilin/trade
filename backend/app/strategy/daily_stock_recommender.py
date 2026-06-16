from __future__ import annotations

from datetime import date

from app.data.manager import DataManager
from app.data.symbols import display_name
from app.signal.composite import CompositeScorer
from app.signal.enhanced import EnhancedSignal
from app.signal.factors import FactorEngine

# 每日推荐股票池：覆盖主要指数成分 + 国家队/国资背景蓝筹
STOCK_CATALOG: list[dict] = [
    {
        "symbol": "600519",
        "name": "贵州茅台",
        "indices": ["hs300"],
        "state_holding": False,
        "sectors": ["消费"],
        "regime_bias": {"bull": 0.06, "neutral": 0.04, "bear": 0.02},
    },
    {
        "symbol": "601318",
        "name": "中国平安",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["金融"],
        "regime_bias": {"bull": 0.05, "neutral": 0.04, "bear": 0.08, "high_vol": 0.06},
    },
    {
        "symbol": "600036",
        "name": "招商银行",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["金融"],
        "regime_bias": {"bull": 0.05, "bear": 0.07, "high_vol": 0.05},
    },
    {
        "symbol": "000858",
        "name": "五粮液",
        "indices": ["hs300"],
        "state_holding": False,
        "sectors": ["消费"],
        "regime_bias": {"bull": 0.06, "neutral": 0.03},
    },
    {
        "symbol": "300750",
        "name": "宁德时代",
        "indices": ["hs300", "cyb"],
        "state_holding": False,
        "sectors": ["新能源"],
        "regime_bias": {"bull": 0.08, "bear": -0.04, "high_vol": -0.03},
    },
    {
        "symbol": "688981",
        "name": "中芯国际",
        "indices": ["kc50", "hs300"],
        "state_holding": True,
        "sectors": ["半导体"],
        "regime_bias": {"bull": 0.07, "neutral": 0.03},
    },
    {
        "symbol": "002230",
        "name": "科大讯飞",
        "indices": ["zz500"],
        "state_holding": False,
        "sectors": ["人工智能"],
        "regime_bias": {"bull": 0.08, "high_vol": -0.02},
    },
    {
        "symbol": "601088",
        "name": "中国神华",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["能源"],
        "regime_bias": {"bear": 0.1, "high_vol": 0.08, "neutral": 0.05},
    },
    {
        "symbol": "600900",
        "name": "长江电力",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["公用事业"],
        "regime_bias": {"bear": 0.09, "high_vol": 0.07, "neutral": 0.06},
    },
    {
        "symbol": "601857",
        "name": "中国石油",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["能源"],
        "regime_bias": {"bear": 0.08, "high_vol": 0.06},
    },
    {
        "symbol": "600028",
        "name": "中国石化",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["能源"],
        "regime_bias": {"bear": 0.07, "high_vol": 0.05},
    },
    {
        "symbol": "601398",
        "name": "工商银行",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["金融"],
        "regime_bias": {"bear": 0.1, "high_vol": 0.08, "neutral": 0.05},
    },
    {
        "symbol": "000333",
        "name": "美的集团",
        "indices": ["hs300"],
        "state_holding": False,
        "sectors": ["消费"],
        "regime_bias": {"bull": 0.05, "neutral": 0.04},
    },
    {
        "symbol": "002475",
        "name": "立讯精密",
        "indices": ["hs300", "zz500"],
        "state_holding": False,
        "sectors": ["半导体", "消费电子"],
        "regime_bias": {"bull": 0.07, "neutral": 0.03},
    },
    {
        "symbol": "601012",
        "name": "隆基绿能",
        "indices": ["hs300"],
        "state_holding": False,
        "sectors": ["新能源"],
        "regime_bias": {"bull": 0.06, "bear": -0.03},
    },
    {
        "symbol": "300059",
        "name": "东方财富",
        "indices": ["cyb", "hs300"],
        "state_holding": False,
        "sectors": ["金融"],
        "regime_bias": {"bull": 0.1, "bear": -0.06, "high_vol": -0.04},
    },
    {
        "symbol": "688041",
        "name": "海光信息",
        "indices": ["kc50"],
        "state_holding": True,
        "sectors": ["半导体", "人工智能"],
        "regime_bias": {"bull": 0.08, "neutral": 0.04},
    },
    {
        "symbol": "601888",
        "name": "中国中免",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["消费"],
        "regime_bias": {"bull": 0.06, "neutral": 0.03},
    },
    {
        "symbol": "600887",
        "name": "伊利股份",
        "indices": ["hs300"],
        "state_holding": False,
        "sectors": ["消费"],
        "regime_bias": {"bear": 0.06, "neutral": 0.05, "high_vol": 0.04},
    },
    {
        "symbol": "601668",
        "name": "中国建筑",
        "indices": ["hs300"],
        "state_holding": True,
        "sectors": ["基建"],
        "regime_bias": {"bear": 0.08, "neutral": 0.05, "high_vol": 0.05},
    },
]

INDEX_LABELS = {
    "hs300": "沪深300",
    "zz500": "中证500",
    "zz1000": "中证1000",
    "kc50": "科创50",
    "cyb": "创业板",
}

REGIME_HINTS = {
    "bull": "市场偏多，侧重指数龙头与景气赛道",
    "bear": "市场偏空，侧重国家队持股与低波蓝筹",
    "neutral": "震荡市，均衡指数成分与国资背景标的",
    "high_vol": "高波动，提高国家持股与防御板块权重",
}


class DailyStockRecommender:
    """每日股票推荐：综合市场环境、指数属性、国家持股偏好与技术综合分。"""

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
        self.factors = FactorEngine()
        self.enhanced = EnhancedSignal()
        self.scorer = CompositeScorer()

    async def recommend(self, limit: int = 10) -> dict:
        regime_data = await self.dm.get_regime()
        regime = regime_data.get("regime", "neutral")
        metrics = regime_data.get("metrics") or {}
        snap_m = await self.dm.market.get_snapshot()
        hot_sectors = snap_m.hot_sectors or []

        items: list[dict] = []
        for meta in STOCK_CATALOG:
            sym = meta["symbol"]
            bars = await self.dm.get_bars(sym, limit=80)
            if not bars:
                continue
            quote = await self.dm.get_quote(sym)
            snap = self.factors.compute(sym, bars)
            snap = await self.enhanced.enrich(sym, bars, snap)
            composite = self.scorer.score(snap)

            regime_bonus = float((meta.get("regime_bias") or {}).get(regime, 0.0))
            index_bonus = self._index_bonus(meta, regime)
            state_bonus = self._state_holding_bonus(meta, regime, metrics)
            sector_bonus = self._sector_bonus(meta, hot_sectors)
            market_bonus = round(regime_bonus + index_bonus + state_bonus + sector_bonus, 4)
            final = round(min(1.0, max(0.0, composite + market_bonus)), 4)

            index_tags = [INDEX_LABELS.get(k, k) for k in meta.get("indices", [])]
            reason = self._reason(meta, regime, composite, market_bonus, index_tags, hot_sectors)

            items.append(
                {
                    "symbol": sym,
                    "name": display_name(sym, meta.get("name") or (quote.name if quote else None)),
                    "composite_score": composite,
                    "market_bonus": market_bonus,
                    "final_score": final,
                    "state_holding": bool(meta.get("state_holding")),
                    "index_tags": index_tags,
                    "change_pct": quote.change_pct if quote else 0.0,
                    "price": quote.price if quote else 0.0,
                    "reason": reason,
                }
            )

        items.sort(key=lambda x: x["final_score"], reverse=True)
        top = items[:limit]
        return {
            "date": date.today().isoformat(),
            "regime": regime,
            "regime_hint": REGIME_HINTS.get(regime, ""),
            "items": top,
            "universe_size": len(STOCK_CATALOG),
        }

    def _index_bonus(self, meta: dict, regime: str) -> float:
        indices = set(meta.get("indices") or [])
        if regime == "bull":
            if "cyb" in indices or "kc50" in indices:
                return 0.04
            if "hs300" in indices:
                return 0.03
        if regime in ("bear", "high_vol") and "hs300" in indices:
            return 0.03
        if regime == "neutral" and indices:
            return 0.02
        return 0.0

    def _state_holding_bonus(self, meta: dict, regime: str, metrics: dict) -> float:
        if not meta.get("state_holding"):
            return 0.0
        flow = float(metrics.get("flow", 0.0))
        if regime in ("bear", "high_vol"):
            return 0.06
        if regime == "neutral":
            return 0.04
        if flow < 0:
            return 0.03
        return 0.02

    def _sector_bonus(self, meta: dict, hot_sectors: list[dict]) -> float:
        stock_sectors = set(meta.get("sectors") or [])
        bonus = 0.0
        for hs in hot_sectors:
            name = hs.get("name") or ""
            ch = float(hs.get("change_pct") or 0)
            if ch <= 0:
                continue
            if name in stock_sectors or any(name in s or s in name for s in stock_sectors):
                bonus = max(bonus, min(0.08, 0.03 + ch / 100))
        return round(bonus, 4)

    def _reason(
        self,
        meta: dict,
        regime: str,
        composite: float,
        market_bonus: float,
        index_tags: list[str],
        hot_sectors: list[dict],
    ) -> str:
        parts: list[str] = []
        if index_tags:
            parts.append("、".join(index_tags[:2]) + "成分")
        if meta.get("state_holding"):
            parts.append("国家队/国资背景")
        if market_bonus >= 0.05:
            parts.append(f"{self._regime_label(regime)}环境适配")
        matched = self._matched_hot_sector(meta, hot_sectors)
        if matched:
            parts.append(f"贴合热点「{matched}」")
        if composite >= 0.55:
            parts.append("技术综合指数靠前")
        elif not parts:
            parts.append("综合评分领先")
        return "，".join(parts[:3])

    def _matched_hot_sector(self, meta: dict, hot_sectors: list[dict]) -> str | None:
        stock_sectors = set(meta.get("sectors") or [])
        for hs in hot_sectors:
            if float(hs.get("change_pct") or 0) <= 0:
                continue
            name = hs.get("name") or ""
            if name in stock_sectors or any(name in s or s in name for s in stock_sectors):
                return name
        return None

    def _regime_label(self, regime: str) -> str:
        return {
            "bull": "偏多",
            "bear": "偏空",
            "neutral": "震荡",
            "high_vol": "高波动",
        }.get(regime, regime)
