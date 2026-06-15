from __future__ import annotations

from functools import lru_cache

from app.backtest.engine import BacktestEngine
from app.data.manager import get_data_manager
from app.executor.paper import PaperExecutor
from app.monitor.ai_news_push import AiNewsPushService
from app.monitor.economic_news import EconomicNewsService
from app.monitor.feishu_push import FeishuPushService
from app.monitor.position_monitor import PositionMonitor
from app.risk.position_manager import PositionManager
from app.risk.settings_store import get_risk_settings_store
from app.signal.emotion import EmotionIndexV2
from app.strategy.entry import EntryEngine
from app.strategy.etf_recommender import EtfRecommender
from app.strategy.screener_v5 import ScreenerV5


@lru_cache
def get_services() -> dict:
    dm = get_data_manager()
    paper = PaperExecutor()
    return {
        "dm": dm,
        "screener": ScreenerV5(dm),
        "etf": EtfRecommender(dm),
        "entry": EntryEngine(),
        "paper": paper,
        "backtest": BacktestEngine(),
        "emotion": EmotionIndexV2(),
        "position_mgr": PositionManager(),
        "risk_settings": get_risk_settings_store(),
        "monitor": PositionMonitor(),
        "feishu": FeishuPushService(),
        "news": EconomicNewsService(),
        "ai_news": AiNewsPushService(),
    }
