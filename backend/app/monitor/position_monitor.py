from __future__ import annotations

from app.core.types import Position, StrategyKind
from app.risk.settings_store import MonitorRules, get_risk_settings_store
from app.strategy.entry import EntryEngine


class PositionMonitor:
    def __init__(self) -> None:
        self.entry = EntryEngine()

    def alerts(
        self,
        positions: list[Position],
        scores: dict[str, float],
        emotion: float,
    ) -> tuple[list[dict], list[dict]]:
        store = get_risk_settings_store()
        risk = store.get()
        out: list[dict] = []
        position_rules: list[dict] = []

        for p in positions:
            rules = risk.effective_monitor(p.symbol)
            position_rules.append(
                {
                    "symbol": p.symbol,
                    "pnl_pct": round(p.pnl_pct, 2),
                    "score": scores.get(p.symbol),
                    "rules": rules.model_dump(),
                    "has_override": p.symbol in risk.symbol_overrides,
                }
            )
            out.extend(self._check_position(p, scores.get(p.symbol, 0.5), emotion, rules))

        return out, position_rules

    def _check_position(
        self,
        p: Position,
        score: float,
        emotion: float,
        rules: MonitorRules,
    ) -> list[dict]:
        found: list[dict] = []

        if rules.enable_stop_loss and p.pnl_pct <= -rules.stop_loss_pct:
            found.append(
                {
                    "symbol": p.symbol,
                    "type": "stop_loss",
                    "reason": f"浮亏达到 {rules.stop_loss_pct:g}%（当前 {p.pnl_pct:.2f}%）",
                    "pnl_pct": round(p.pnl_pct, 2),
                    "threshold": {"stop_loss_pct": rules.stop_loss_pct},
                }
            )

        if rules.enable_take_profit and p.pnl_pct >= rules.take_profit_pct:
            found.append(
                {
                    "symbol": p.symbol,
                    "type": "take_profit",
                    "reason": f"浮盈达到 {rules.take_profit_pct:g}%（当前 {p.pnl_pct:.2f}%）",
                    "pnl_pct": round(p.pnl_pct, 2),
                    "threshold": {"take_profit_pct": rules.take_profit_pct},
                }
            )

        if rules.enable_sell_signal:
            old = self.entry.sell_threshold
            try:
                self.entry.sell_threshold = rules.sell_score_threshold
                intent = self.entry.decide(p.symbol, score, StrategyKind.OVERSOLD_REBOUND, True, emotion)
            finally:
                self.entry.sell_threshold = old
            if intent and intent.side.value == "sell":
                found.append(
                    {
                        "symbol": p.symbol,
                        "type": "sell_signal",
                        "reason": intent.reason,
                        "pnl_pct": round(p.pnl_pct, 2),
                        "threshold": {"sell_score_threshold": rules.sell_score_threshold},
                    }
                )

        return found
