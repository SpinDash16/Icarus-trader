from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .broker import AlpacaBroker, build_client
from .engine import Skip, Submit, decide

ET = ZoneInfo("America/New_York")
HALT_FILE = Path(__file__).resolve().parent.parent / "HALT"


def _log(record: dict) -> None:
    record["ts"] = datetime.now(timezone.utc).isoformat()
    record["env"] = os.environ.get("ALPACA_ENV", "paper")
    print(json.dumps(record), flush=True)


def main() -> int:
    halted = HALT_FILE.exists()
    today_et = datetime.now(ET).date()

    try:
        client = build_client()
    except SystemExit:
        raise
    except Exception as e:
        _log({"decision": "error", "phase": "client_init", "error": repr(e)})
        return 1

    broker = AlpacaBroker(client)

    try:
        action = decide(broker=broker, today=today_et, halted=halted)
    except Exception as e:
        _log({"decision": "error", "phase": "decide", "error": repr(e)})
        return 1

    if isinstance(action, Skip):
        _log({"decision": "skipped", "reason": action.reason})
        return 0

    assert isinstance(action, Submit)
    try:
        result = broker.submit_notional_buy(symbol=action.symbol, notional=action.notional)
    except Exception as e:
        _log(
            {
                "decision": "rejected",
                "symbol": action.symbol,
                "notional": action.notional,
                "error": repr(e),
            }
        )
        return 0

    _log(
        {
            "decision": "submitted",
            "symbol": action.symbol,
            "notional": action.notional,
            "order_id": result.order_id,
            "status": result.status,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
