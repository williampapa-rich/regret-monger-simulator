from __future__ import annotations

import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from regret.domain.enums import Market

DEFAULT_FEES_PATH = Path(__file__).resolve().parent.parent / "config" / "fees.toml"


@dataclass(frozen=True)
class FeeTable:
    rates: dict[Market, Decimal]

    @classmethod
    def load(cls, path: Path | None = None) -> "FeeTable":
        target = path or DEFAULT_FEES_PATH
        with target.open("rb") as f:
            raw = tomllib.load(f)
        rates_raw = raw.get("rates", {})
        rates: dict[Market, Decimal] = {}
        for market in Market:
            if market.value not in rates_raw:
                raise ValueError(f"fees.toml에 {market.value} 누락")
            value = rates_raw[market.value]
            # toml의 문자열을 Decimal로 보존 (float 경유 금지)
            rates[market] = Decimal(str(value))
        return cls(rates=rates)

    def get(self, market: Market) -> Decimal:
        return self.rates[market]
