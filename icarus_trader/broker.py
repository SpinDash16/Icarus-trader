from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderStatus, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest

SYMBOL = "TQQQ"
ET = ZoneInfo("America/New_York")

# Orders that never resulted in capital leaving the account. If today's only
# TQQQ orders are in these states, we should still submit a fresh buy.
_DEAD_STATUSES = {OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED}


@dataclass(frozen=True)
class SubmitResult:
    order_id: str
    status: str


class AlpacaBroker:
    def __init__(self, client: TradingClient) -> None:
        self._client = client

    def has_tqqq_order_today(self, today: date) -> bool:
        after = datetime.combine(today, datetime.min.time(), tzinfo=ET)
        req = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            after=after,
            symbols=[SYMBOL],
        )
        orders = self._client.get_orders(filter=req)
        return any(o.status not in _DEAD_STATUSES for o in orders)

    def submit_notional_buy(self, symbol: str, notional: float) -> SubmitResult:
        req = MarketOrderRequest(
            symbol=symbol,
            notional=notional,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        order = self._client.submit_order(order_data=req)
        return SubmitResult(order_id=str(order.id), status=str(order.status))


def build_client() -> TradingClient:
    env = os.environ.get("ALPACA_ENV", "paper").lower()
    if env not in ("paper", "live"):
        raise SystemExit(f"ALPACA_ENV must be 'paper' or 'live', got: {env!r}")
    try:
        key = os.environ["APCA_API_KEY_ID"]
        secret = os.environ["APCA_API_SECRET_KEY"]
    except KeyError as missing:
        raise SystemExit(f"Missing required env var: {missing.args[0]}") from None
    return TradingClient(api_key=key, secret_key=secret, paper=(env == "paper"))
