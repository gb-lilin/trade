from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.types import SignalSide, StrategyKind, TradeIntent
from app.deps import get_services

router = APIRouter(prefix="/api", tags=["api"])


class BacktestRequest(BaseModel):
    symbol: str = "600519"
    limit: int = Field(default=120, ge=30, le=500)


class PaperTradeRequest(BaseModel):
    symbol: str
    side: str
    price: float | None = None
    weight: float = Field(default=0.1, ge=0.01, le=0.25)


@router.get("/health")
async def health():
    return {"status": "ok", "version": "5.1"}


@router.get("/dashboard")
async def dashboard():
    s = get_services()
    dm, paper, screener, emotion = s["dm"], s["paper"], s["screener"], s["emotion"]
    regime = await dm.get_regime()
    index_bars = await dm.get_bars("000001", limit=80)
    emo = emotion.compute(index_bars)
    picks = await screener.scan()
    news_svc = s["news"]
    news_data = news_svc.list_items(limit=5)
    if not news_data.get("items"):
        refreshed = await news_svc.refresh()
        news_data = {
            "updated_at": refreshed.get("updated_at"),
            "items": refreshed.get("items", [])[:5],
        }
    snap = paper.snapshot()
    prices = {}
    for p in snap["positions"]:
        q = await dm.get_quote(p["symbol"])
        if q:
            prices[p["symbol"]] = q.price
    if prices:
        paper.update_prices(prices)
        snap = paper.snapshot()
    snap_m = await dm.market.get_snapshot()
    market = {
        "breadth": snap_m.breadth.__dict__,
        "hot_sectors": snap_m.hot_sectors,
        "dragon_tiger": snap_m.dragon_tiger,
    }
    return {
        "regime": regime,
        "emotion": emo,
        "market": market,
        "picks": picks[:10],
        "portfolio": snap,
        "news": news_data,
    }


@router.get("/scan")
async def scan(symbols: str | None = None):
    s = get_services()
    sym_list = [x.strip() for x in symbols.split(",")] if symbols else None
    return {"items": await s["screener"].scan(sym_list)}


@router.get("/etf/recommend")
async def etf_recommend(limit: int = 10):
    s = get_services()
    lim = max(3, min(limit, 20))
    return await s["etf"].recommend(limit=lim)


@router.get("/quote/{symbol}")
async def quote(symbol: str):
    s = get_services()
    q = await s["dm"].get_quote(symbol)
    if not q:
        raise HTTPException(404, "无法获取行情")
    return {
        "symbol": q.symbol,
        "name": q.name,
        "price": q.price,
        "change_pct": q.change_pct,
        "volume": q.volume,
    }


@router.get("/portfolio")
async def portfolio():
    s = get_services()
    paper = s["paper"]
    dm = s["dm"]
    snap = paper.snapshot()
    prices = {}
    for p in snap["positions"]:
        q = await dm.get_quote(p["symbol"])
        if q:
            prices[p["symbol"]] = q.price
    if prices:
        paper.update_prices(prices)
        snap = paper.snapshot()
    return snap


@router.post("/paper/trade")
async def paper_trade(body: PaperTradeRequest):
    s = get_services()
    dm, paper, entry, pos_mgr, screener = s["dm"], s["paper"], s["entry"], s["position_mgr"], s["screener"]
    q = await dm.get_quote(body.symbol)
    if not q:
        raise HTTPException(404, "无法获取行情")
    price = body.price or q.price
    bars = await dm.get_bars(body.symbol, limit=60)
    regime = await dm.get_regime()
    has_pos = body.symbol in paper.positions
    scan_one = await screener.scan([body.symbol])
    score = scan_one[0]["composite_score"] if scan_one else 0.5
    strategy = StrategyKind(scan_one[0]["strategy"]) if scan_one else StrategyKind.OVERSOLD_REBOUND
    emo = s["emotion"].compute(await dm.get_bars("000001", 80))
    side = SignalSide(body.side.lower())
    if side == SignalSide.BUY:
        intent = entry.decide(body.symbol, score, strategy, has_pos, emo["emotion"])
        if not intent:
            intent = TradeIntent(
                symbol=body.symbol,
                side=SignalSide.BUY,
                strategy=strategy,
                score=score,
                reason="manual",
                suggested_weight=body.weight,
            )
        weight = pos_mgr.final_weight(body.weight, regime["environment_multiplier"], score, bars)
        result = paper.execute(intent, price, weight)
    else:
        intent = TradeIntent(
            symbol=body.symbol,
            side=SignalSide.SELL,
            strategy=strategy,
            score=score,
            reason="manual",
        )
        result = paper.execute(intent, price, 0)
    return result


@router.post("/backtest")
async def backtest(body: BacktestRequest):
    s = get_services()
    bars = await s["dm"].get_bars(body.symbol, limit=body.limit)
    r = s["backtest"].run(body.symbol, bars)
    return {
        "symbol": body.symbol,
        "total_return_pct": r.total_return_pct,
        "max_drawdown_pct": r.max_drawdown_pct,
        "sharpe": r.sharpe,
        "trades": r.trades,
        "equity_curve": r.equity_curve,
    }


@router.get("/monitor/alerts")
async def monitor_alerts():
    s = get_services()
    paper, dm, monitor = s["paper"], s["dm"], s["monitor"]
    snap = paper.snapshot()
    positions = list(paper.positions.values())
    scores = {}
    for p in positions:
        scan = await s["screener"].scan([p.symbol])
        if scan:
            scores[p.symbol] = scan[0]["composite_score"]
    emo = s["emotion"].compute(await dm.get_bars("000001", 80))
    alerts, position_rules = monitor.alerts(positions, scores, emo["emotion"])
    risk_settings = s["risk_settings"].get()
    return {
        "emotion": emo,
        "alerts": alerts,
        "portfolio": snap,
        "position_rules": position_rules,
        "risk_settings": risk_settings.model_dump(),
    }


@router.get("/risk/params")
async def risk_params():
    from app.config import settings

    cfg = get_services()["risk_settings"].get()
    return {
        "max_position_pct": cfg.max_position_pct,
        "max_total_exposure": cfg.max_total_exposure,
        "paper_initial_cash": settings.paper_initial_cash,
    }


class MonitorRulesUpdate(BaseModel):
    stop_loss_pct: float | None = Field(default=None, ge=0, le=80)
    take_profit_pct: float | None = Field(default=None, ge=0, le=500)
    sell_score_threshold: float | None = Field(default=None, ge=0, le=1)
    enable_stop_loss: bool | None = None
    enable_take_profit: bool | None = None
    enable_sell_signal: bool | None = None


class RiskSettingsUpdate(BaseModel):
    max_position_pct: float | None = Field(default=None, gt=0, le=1)
    max_total_exposure: float | None = Field(default=None, gt=0, le=1)
    default_monitor: MonitorRulesUpdate | None = None


class SymbolOverrideBody(BaseModel):
    rules: MonitorRulesUpdate


@router.get("/risk/settings")
async def get_risk_settings():
    store = get_services()["risk_settings"]
    return store.get().model_dump()


@router.put("/risk/settings")
async def put_risk_settings(body: RiskSettingsUpdate):
    store = get_services()["risk_settings"]
    patch: dict = {}
    if body.max_position_pct is not None:
        patch["max_position_pct"] = body.max_position_pct
    if body.max_total_exposure is not None:
        patch["max_total_exposure"] = body.max_total_exposure
    if body.default_monitor:
        patch["default_monitor"] = body.default_monitor.model_dump(exclude_none=True)
    return store.update(patch).model_dump()


@router.put("/risk/settings/symbol/{symbol}")
async def put_symbol_risk_settings(symbol: str, body: SymbolOverrideBody):
    from app.risk.settings_store import SymbolMonitorOverride

    store = get_services()["risk_settings"]
    ov = SymbolMonitorOverride(**body.rules.model_dump(exclude_none=True))
    return store.set_symbol_override(symbol, ov).model_dump()


@router.delete("/risk/settings/symbol/{symbol}")
async def delete_symbol_risk_settings(symbol: str):
    store = get_services()["risk_settings"]
    return store.clear_symbol_override(symbol).model_dump()


@router.get("/news")
async def news_list(limit: int = 30, refresh: bool = False):
    s = get_services()
    svc = s["news"]
    if refresh:
        data = await svc.refresh()
        return {
            "updated_at": data.get("updated_at"),
            "items": data.get("items", [])[:limit],
            "count": min(limit, len(data.get("items", []))),
        }
    data = svc.list_items(limit=limit)
    if not data.get("items"):
        data = await svc.refresh()
        return {
            "updated_at": data.get("updated_at"),
            "items": data.get("items", [])[:limit],
            "count": min(limit, len(data.get("items", []))),
        }
    return data


@router.post("/news/refresh")
async def news_refresh():
    s = get_services()
    data = await s["news"].refresh()
    return {"updated_at": data.get("updated_at"), "count": len(data.get("items", []))}


@router.post("/news/push")
async def news_push(max_items: int = 8):
    s = get_services()
    return await s["ai_news"].push_latest(max_items=max_items)


@router.post("/news/push-refresh")
async def news_push_refresh(max_items: int = 8):
    s = get_services()
    return await s["ai_news"].refresh_and_push(max_items=max_items)
