from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.core.types import Position, TradeIntent, SignalSide
from app.risk.validator import RiskValidator


class PaperExecutor:
    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or Path(__file__).resolve().parents[2] / "data" / "paper_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.validator = RiskValidator()
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.cash = float(raw.get("cash", settings.paper_initial_cash))
            self.positions = {
                p["symbol"]: Position(
                    symbol=p["symbol"],
                    name=p.get("name", p["symbol"]),
                    shares=int(p["shares"]),
                    avg_cost=float(p["avg_cost"]),
                    current_price=float(p.get("current_price", p["avg_cost"])),
                )
                for p in raw.get("positions", [])
            }
        else:
            self.cash = settings.paper_initial_cash
            self.positions: dict[str, Position] = {}

    def _save(self) -> None:
        payload = {
            "cash": self.cash,
            "positions": [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "shares": p.shares,
                    "avg_cost": p.avg_cost,
                    "current_price": p.current_price,
                }
                for p in self.positions.values()
            ],
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def snapshot(self) -> dict:
        mv = sum(p.market_value for p in self.positions.values())
        return {
            "cash": round(self.cash, 2),
            "market_value": round(mv, 2),
            "equity": round(self.cash + mv, 2),
            "positions": [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "shares": p.shares,
                    "avg_cost": p.avg_cost,
                    "current_price": p.current_price,
                    "market_value": round(p.market_value, 2),
                    "pnl_pct": round(p.pnl_pct, 2),
                }
                for p in self.positions.values()
            ],
        }

    def update_prices(self, prices: dict[str, float]) -> None:
        for sym, p in self.positions.items():
            if sym in prices:
                p.current_price = prices[sym]
        self._save()

    def execute(self, intent: TradeIntent, price: float, weight: float) -> dict:
        if intent.side == SignalSide.BUY:
            equity = self.cash + sum(x.market_value for x in self.positions.values())
            order_value = equity * weight
            vr = self.validator.validate_buy(intent, self.cash, list(self.positions.values()), order_value)
            if not vr.ok:
                return {"ok": False, "message": vr.message}
            shares = int(order_value / price / 100) * 100
            if shares <= 0:
                return {"ok": False, "message": "下单数量过小"}
            cost = shares * price
            self.cash -= cost
            pos = self.positions.get(intent.symbol)
            if pos:
                total = pos.shares + shares
                pos.avg_cost = (pos.avg_cost * pos.shares + cost) / total
                pos.shares = total
                pos.current_price = price
            else:
                self.positions[intent.symbol] = Position(
                    symbol=intent.symbol, name=intent.symbol, shares=shares, avg_cost=price, current_price=price
                )
            self._save()
            return {"ok": True, "side": "buy", "shares": shares, "price": price}

        pos = self.positions.get(intent.symbol)
        shares = pos.shares if pos else 0
        vr = self.validator.validate_sell(intent, pos, shares)
        if not vr.ok:
            return {"ok": False, "message": vr.message}
        proceeds = shares * price
        self.cash += proceeds
        del self.positions[intent.symbol]
        self._save()
        return {"ok": True, "side": "sell", "shares": shares, "price": price}
