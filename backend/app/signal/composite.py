from __future__ import annotations

from app.core.types import FactorSnapshot
from app.signal.factors import FACTOR_GROUPS


class CompositeScorer:
    GROUP_WEIGHTS = {
        "momentum": 0.22,
        "trend": 0.2,
        "volatility": 0.12,
        "volume": 0.15,
        "reversal": 0.18,
        "strength": 0.13,
    }

    def score(self, snap: FactorSnapshot) -> float:
        total_w = 0.0
        acc = 0.0
        for group, keys in FACTOR_GROUPS.items():
            gw = self.GROUP_WEIGHTS.get(group, 0.1)
            vals = [snap.factors.get(k, 0.0) for k in keys if k in snap.factors]
            if not vals:
                continue
            group_score = sum(vals) / len(vals)
            if group == "volatility":
                group_score = 1.0 - min(1.0, group_score * 5)
            acc += group_score * gw
            total_w += gw
        composite = acc / total_w if total_w else 0.0
        snap.composite_score = round(max(0.0, min(1.0, composite)), 4)
        return snap.composite_score
