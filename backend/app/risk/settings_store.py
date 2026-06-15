from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings as app_settings


class MonitorRules(BaseModel):
    stop_loss_pct: float = Field(default=8.0, ge=0, le=80, description="浮亏达到该百分比触发止损告警")
    take_profit_pct: float = Field(default=15.0, ge=0, le=500, description="浮盈达到该百分比触发止盈告警")
    sell_score_threshold: float = Field(
        default=0.42, ge=0, le=1, description="综合分低于该值触发卖出信号告警"
    )
    enable_stop_loss: bool = True
    enable_take_profit: bool = True
    enable_sell_signal: bool = True


class SymbolMonitorOverride(BaseModel):
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    sell_score_threshold: float | None = None
    enable_stop_loss: bool | None = None
    enable_take_profit: bool | None = None
    enable_sell_signal: bool | None = None


class RiskSettings(BaseModel):
    max_position_pct: float = Field(default=0.25, gt=0, le=1)
    max_total_exposure: float = Field(default=0.95, gt=0, le=1)
    default_monitor: MonitorRules = Field(default_factory=MonitorRules)
    symbol_overrides: dict[str, SymbolMonitorOverride] = Field(default_factory=dict)

    def effective_monitor(self, symbol: str) -> MonitorRules:
        base = self.default_monitor.model_dump()
        ov = self.symbol_overrides.get(symbol)
        if ov:
            for k, v in ov.model_dump(exclude_none=True).items():
                base[k] = v
        return MonitorRules(**base)


class RiskSettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parents[2] / "data" / "risk_settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def defaults(self) -> RiskSettings:
        return RiskSettings(
            max_position_pct=app_settings.max_position_pct,
            max_total_exposure=app_settings.max_total_exposure,
        )

    def get(self) -> RiskSettings:
        if not self.path.exists():
            return self.defaults()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return RiskSettings.model_validate(raw)

    def save(self, data: RiskSettings) -> RiskSettings:
        self.path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
        return data

    def update(self, patch: dict[str, Any]) -> RiskSettings:
        current = self.get()
        merged = current.model_dump()
        for key, val in patch.items():
            if key == "default_monitor" and isinstance(val, dict):
                merged["default_monitor"] = {
                    **merged.get("default_monitor", {}),
                    **val,
                }
            elif key == "symbol_overrides" and isinstance(val, dict):
                merged["symbol_overrides"] = val
            else:
                merged[key] = val
        saved = RiskSettings.model_validate(merged)
        return self.save(saved)

    def set_symbol_override(self, symbol: str, override: SymbolMonitorOverride | None) -> RiskSettings:
        current = self.get()
        sym = symbol.strip()
        overrides = dict(current.symbol_overrides)
        if override is None:
            overrides.pop(sym, None)
        elif not override.model_dump(exclude_none=True):
            overrides.pop(sym, None)
        else:
            prev = overrides.get(sym, SymbolMonitorOverride())
            overrides[sym] = SymbolMonitorOverride(
                **{**prev.model_dump(), **override.model_dump(exclude_none=True)}
            )
        return self.save(current.model_copy(update={"symbol_overrides": overrides}))

    def clear_symbol_override(self, symbol: str) -> RiskSettings:
        return self.set_symbol_override(symbol, None)


_store: RiskSettingsStore | None = None


def get_risk_settings_store() -> RiskSettingsStore:
    global _store
    if _store is None:
        _store = RiskSettingsStore()
    return _store
