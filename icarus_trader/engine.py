from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

SYMBOL = "TQQQ"
NOTIONAL_USD = 25


@dataclass(frozen=True)
class Submit:
    symbol: str = SYMBOL
    notional: int = NOTIONAL_USD


@dataclass(frozen=True)
class Skip:
    reason: str


Action = Submit | Skip


class Broker(Protocol):
    def has_tqqq_order_today(self, today: date) -> bool: ...


def decide(*, broker: Broker, today: date, halted: bool) -> Action:
    if halted:
        return Skip(reason="halted")
    if broker.has_tqqq_order_today(today):
        return Skip(reason="already_filled")
    return Submit()
