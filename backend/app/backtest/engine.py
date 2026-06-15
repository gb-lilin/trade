from __future__ import annotations

import random

from app.core.types import BacktestResult, Bar


class BacktestEngine:
    def run(self, symbol: str, bars: list[Bar], initial_cash: float = 1_000_000.0) -> BacktestResult:
        if len(bars) < 30:
            return BacktestResult(0, 0, 0, 0)

        cash = initial_cash
        shares = 0
        equity_curve: list[dict] = []
        peak = initial_cash
        max_dd = 0.0
        trades = 0

        for i in range(20, len(bars)):
            window = bars[: i + 1]
            closes = [b.close for b in window]
            ma5 = sum(closes[-5:]) / 5
            ma20 = sum(closes[-20:]) / 20
            price = closes[-1]
            if shares == 0 and ma5 > ma20 * 1.01:
                shares = int(cash * 0.3 / price / 100) * 100
                if shares > 0:
                    cash -= shares * price
                    trades += 1
            elif shares > 0 and ma5 < ma20 * 0.99:
                cash += shares * price
                shares = 0
                trades += 1
            equity = cash + shares * price
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100 if peak else 0
            max_dd = max(max_dd, dd)
            equity_curve.append({"date": window[-1].date, "equity": round(equity, 2)})

        final = cash + shares * bars[-1].close
        ret = (final - initial_cash) / initial_cash * 100
        rets = []
        for j in range(1, len(equity_curve)):
            prev = equity_curve[j - 1]["equity"]
            cur = equity_curve[j]["equity"]
            if prev:
                rets.append((cur - prev) / prev)
        sharpe = 0.0
        if rets:
            mean = sum(rets) / len(rets)
            var = sum((r - mean) ** 2 for r in rets) / len(rets)
            std = var**0.5
            sharpe = (mean / std * (252**0.5)) if std else 0.0

        return BacktestResult(
            total_return_pct=round(ret, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe=round(sharpe, 2),
            trades=trades,
            equity_curve=equity_curve[-120:],
        )
