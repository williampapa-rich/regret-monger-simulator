"""Portfolio ↔ JSON 영속성."""
from __future__ import annotations

from pathlib import Path

from regret.domain.models import Portfolio


def save(portfolio: Portfolio, path: Path) -> None:
    path.write_text(portfolio.model_dump_json(indent=2), encoding="utf-8")


def load(path: Path) -> Portfolio:
    return Portfolio.model_validate_json(path.read_text(encoding="utf-8"))
