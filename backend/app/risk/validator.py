from __future__ import annotations

from dataclasses import dataclass

from app.core.types import TradeIntent, Position
from app.risk.settings_store import get_risk_settings_store


@dataclass
class ValidationResult:
    ok: bool
    message: str = ""


class RiskValidator:
    def validate_buy(
        self,
        intent: TradeIntent,
        cash: float,
        positions: list[Position],
        order_value: float,
    ) -> ValidationResult:
        cfg = get_risk_settings_store().get()
        if order_value > cash:
            return ValidationResult(False, "可用资金不足")
        total_mv = sum(p.market_value for p in positions) + order_value
        equity = cash + sum(p.market_value for p in positions)
        if equity > 0 and total_mv / equity > cfg.max_total_exposure:
            return ValidationResult(False, f"总仓位超过上限 {cfg.max_total_exposure:.0%}")
        if equity > 0 and order_value / equity > cfg.max_position_pct:
            return ValidationResult(False, f"单票仓位超过上限 {cfg.max_position_pct:.0%}")
        return ValidationResult(True, "通过")

    def validate_sell(self, intent: TradeIntent, pos: Position | None, shares: int) -> ValidationResult:
        if not pos or pos.shares < shares:
            return ValidationResult(False, "持仓不足")
        return ValidationResult(True, "通过")
