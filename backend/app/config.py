from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Quant Trading System V5.1"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    tushare_token: str = ""
    feishu_webhook: str = ""

    news_rss_urls: str = ""
    news_fresh_hours: float = 24.0
    openai_api_key: str = ""

    paper_initial_cash: float = 1_000_000.0
    max_position_pct: float = 0.25
    max_total_exposure: float = 0.95


settings = Settings()
