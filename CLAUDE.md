# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Icarus-trader is a Python trading engine that executes one fixed strategy on Alpaca: dollar-cost average into TQQQ by submitting a **$25 notional market buy once per trading day**, shortly after US market open. The engine is intentionally narrow — not a generic framework.

Status at time of writing: the repo is empty. The sections below describe the intended shape; update them as code lands.

## Stack

- Python, managed with `uv`
- `alpaca-py` for the broker API
- `pytest` for tests, `ruff` for lint/format

## Commands

- Install / sync deps: `uv sync`
- Run the engine (single production invocation): `uv run python -m icarus_trader`
- Run all tests: `uv run pytest`
- Run a single test: `uv run pytest tests/test_engine.py::test_name`
- Lint + format check: `uv run ruff check . && uv run ruff format --check .`

## How it runs

The engine is a **one-shot script**, not a daemon. An external scheduler (cron or systemd timer) invokes `python -m icarus_trader` once per weekday ~1 minute after US market open (9:31 ET). Sample systemd units and an env-file template live in `deploy/`. Each run:

1. Checks the kill-switch file.
2. Asks Alpaca whether a TQQQ buy has already been submitted/filled today; exits idempotently if so.
3. Submits a notional market order: `symbol=TQQQ`, `notional=25`, `side=buy`, `time_in_force=day`.
4. Writes one structured log line and exits.

Do not introduce an in-process scheduler, daemon loop, or persistent state file. **The scheduler owns timing; Alpaca owns state.**

## Environment

Configuration is env-var only (no config file):

- `ALPACA_ENV` — `paper` (default) or `live`. Selects the Alpaca base URL. Flipping to `live` is an explicit ops action; never default to live in code.
- `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` — Alpaca credentials.

## Conventions & invariants

- **Strategy parameters are hardcoded.** Symbol (`TQQQ`), amount (`$25`), side (buy), order type (notional market), cadence (once per trading day). Do not parameterize these without an explicit request — configurability is a non-goal.
- **Trust Alpaca as the source of truth.** Do not implement local market-calendar, holiday, or buying-power checks. If the order is invalid, let Alpaca reject it and record the rejection reason. This keeps the engine dumb and the audit trail honest.
- **Idempotency comes from Alpaca's order history**, not a local file. Before submitting, query today's orders/activities for any TQQQ buy (filled *or* open) and skip if one exists. Querying survives restarts, reinstalls, and clock drift.
- **Kill-switch: a file named `HALT` at the repo root.** If present, exit immediately with a log line and no API calls. Lets the operator stop trading without a code change or redeploy.
- **One structured log line per invocation** covering at minimum: UTC timestamp, `ALPACA_ENV`, decision (submitted / skipped-already-filled / skipped-halted / rejected / error), rejection or error reason, and order ID when applicable. This is the audit trail — treat the schema as stable once chosen.
- **No retries on order submission.** Submitted orders either fill or get rejected; do not loop. Tomorrow's run is the next attempt.

## Architecture

Codebase is small; discipline matters more than layout. Suggested split:

- `icarus_trader/__main__.py` — entry point: load env, construct client, run the decision flow, exit.
- `icarus_trader/engine.py` — **pure decision logic**: given a broker interface + "now", returns an action. No network, no `os.environ`, no logging side-effects. Fully unit-testable.
- `icarus_trader/broker.py` — thin wrapper over `alpaca-py` exposing only the two calls used (list today's TQQQ orders, submit notional order). Everything else goes through here so tests can fake it.
- `tests/` — unit-test `engine.py` against a fake broker. Tests must not hit the real Alpaca API.

Keep the decision logic free of I/O so every branch (halted, already-filled, submit, rejected) is exercised in tests without mocking the network.
