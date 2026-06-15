from __future__ import annotations

from app.data.manager import DataManager
from app.data.symbols import display_name
from app.signal.composite import CompositeScorer
from app.signal.enhanced import EnhancedSignal
from app.signal.factors import FactorEngine

# 常见 A 股 ETF：宽基 / 行业 / 跨境 / 商品 / 债券 / 红利
ETF_CATALOG: list[dict] = [
    {"symbol": "510300", "name": "沪深300ETF", "category": "broad", "regime_bias": {"bull": 0.08, "neutral": 0.05}},
    {"symbol": "510500", "name": "中证500ETF", "category": "broad", "regime_bias": {"bull": 0.1, "neutral": 0.04}},
    {"symbol": "512100", "name": "中证1000ETF", "category": "broad", "regime_bias": {"bull": 0.12, "high_vol": -0.04}},
    {"symbol": "159915", "name": "创业板ETF", "category": "growth", "regime_bias": {"bull": 0.12, "bear": -0.08}},
    {"symbol": "588000", "name": "科创50ETF", "category": "growth", "regime_bias": {"bull": 0.1, "bear": -0.06}},
    {"symbol": "512880", "name": "证券ETF", "category": "sector", "regime_bias": {"bull": 0.14, "bear": -0.1}},
    {"symbol": "512690", "name": "酒ETF", "category": "sector", "regime_bias": {"bull": 0.06, "neutral": 0.04}},
    {"symbol": "515790", "name": "光伏ETF", "category": "sector", "regime_bias": {"bull": 0.08, "high_vol": -0.05}},
    {"symbol": "512890", "name": "红利低波ETF", "category": "dividend", "regime_bias": {"bear": 0.12, "neutral": 0.08, "high_vol": 0.06}},
    {"symbol": "518880", "name": "黄金ETF", "category": "commodity", "regime_bias": {"bear": 0.1, "high_vol": 0.12}},
    {"symbol": "513100", "name": "纳指ETF", "category": "cross_border", "regime_bias": {"bull": 0.08, "neutral": 0.05}},
    {"symbol": "159920", "name": "恒生ETF", "category": "cross_border", "regime_bias": {"neutral": 0.04, "bear": 0.06}},
    {"symbol": "511260", "name": "十年国债ETF", "category": "bond", "regime_bias": {"bear": 0.14, "high_vol": 0.1}},
]

CATEGORY_LABELS = {
    "broad": "宽基",
    "growth": "成长",
    "sector": "行业",
    "dividend": "红利",
    "commodity": "商品",
    "cross_border": "跨境",
    "bond": "债券",
}

REGIME_HINTS = {
    "bull": "偏多环境，侧重宽基与成长弹性",
    "bear": "偏空环境，侧重红利、债券与黄金",
    "neutral": "震荡环境，均衡配置宽基与红利",
    "high_vol": "高波动环境，降低高 beta，增配防御与商品",
}


class EtfRecommender:
    """结合技术因子与市场环境，对 ETF 池排序推荐。"""

    def __init__(self, dm: DataManager) -> None:
        self.dm = dm
        self.factors = FactorEngine()
        self.enhanced = EnhancedSignal()
        self.scorer = CompositeScorer()

    async def recommend(self, limit: int = 10) -> dict:
        regime_data = await self.dm.get_regime()
        regime = regime_data.get("regime", "neutral")
        items: list[dict] = []

        for meta in ETF_CATALOG:
            sym = meta["symbol"]
            bars = await self.dm.get_bars(sym, limit=80)
            if not bars:
                continue
            quote = await self.dm.get_quote(sym)
            snap = self.factors.compute(sym, bars)
            snap = await self.enhanced.enrich(sym, bars, snap)
            composite = self.scorer.score(snap)
            bias_map = meta.get("regime_bias") or {}
            regime_bonus = float(bias_map.get(regime, 0.0))
            final = round(min(1.0, max(0.0, composite + regime_bonus)), 4)
            reason = self._reason(meta, snap.factors, regime, regime_bonus)
            items.append(
                {
                    "symbol": sym,
                    "name": display_name(sym, meta.get("name") or (quote.name if quote else None)),
                    "category": meta["category"],
                    "category_label": CATEGORY_LABELS.get(meta["category"], meta["category"]),
                    "composite_score": composite,
                    "regime_bonus": round(regime_bonus, 4),
                    "final_score": final,
                    "change_pct": quote.change_pct if quote else 0.0,
                    "price": quote.price if quote else 0.0,
                    "reason": reason,
                    "factors": snap.factors,
                }
            )

        items.sort(key=lambda x: x["final_score"], reverse=True)
        top = items[:limit]
        return {
            "regime": regime,
            "regime_hint": REGIME_HINTS.get(regime, ""),
            "environment_multiplier": regime_data.get("environment_multiplier"),
            "items": top,
            "universe_size": len(ETF_CATALOG),
        }

    def _reason(self, meta: dict, factors: dict, regime: str, bonus: float) -> str:
        parts: list[str] = []
        if bonus > 0:
            parts.append(f"当前{self._regime_label(regime)}下品类适配")
        momentum = factors.get("momentum_20", 0)
        oversold = factors.get("oversold_score", 0)
        trend = factors.get("ma_trend", 0)
        if oversold >= 0.45:
            parts.append("超跌修复信号")
        elif momentum >= 0.55:
            parts.append("中期动量偏强")
        elif trend >= 0.55:
            parts.append("均线趋势向好")
        else:
            parts.append("因子综合评分靠前")
        cat = CATEGORY_LABELS.get(meta["category"], meta["category"])
        parts.append(f"{cat}配置")
        return "，".join(parts[:3])

    def _regime_label(self, regime: str) -> str:
        return {
            "bull": "偏多",
            "bear": "偏空",
            "neutral": "震荡",
            "high_vol": "高波动",
        }.get(regime, regime)
