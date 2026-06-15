from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.types import Bar, Quote


class DataSource(ABC):
    name: str = "base"

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote | None:
        ...

    @abstractmethod
    async def get_bars(self, symbol: str, limit: int = 120) -> list[Bar]:
        ...
