from dataclasses import dataclass
from datetime import date

from icarus_trader.engine import NOTIONAL_USD, SYMBOL, Skip, Submit, decide

TODAY = date(2025, 6, 2)


@dataclass
class FakeBroker:
    has_order: bool = False

    def has_tqqq_order_today(self, today: date) -> bool:
        return self.has_order


class ExplodingBroker:
    def has_tqqq_order_today(self, today: date) -> bool:
        raise AssertionError("broker should not be queried when halted")


def test_halted_skips_without_broker_call():
    action = decide(broker=ExplodingBroker(), today=TODAY, halted=True)
    assert action == Skip(reason="halted")


def test_already_filled_skips():
    action = decide(broker=FakeBroker(has_order=True), today=TODAY, halted=False)
    assert action == Skip(reason="already_filled")


def test_clean_path_submits_tqqq_25_notional():
    action = decide(broker=FakeBroker(has_order=False), today=TODAY, halted=False)
    assert isinstance(action, Submit)
    assert action.symbol == SYMBOL == "TQQQ"
    assert action.notional == NOTIONAL_USD == 25


def test_halted_takes_precedence_over_already_filled():
    action = decide(broker=FakeBroker(has_order=True), today=TODAY, halted=True)
    assert action == Skip(reason="halted")
