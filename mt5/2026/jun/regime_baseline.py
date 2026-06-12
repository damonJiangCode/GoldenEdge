from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any

import MetaTrader5 as mt5  # type: ignore
import pandas as pd  # type: ignore


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[2]
LOG_DIR = BASE_DIR / "logs"
EVENT_FILE = LOG_DIR / "regime_baseline_events.jsonl"
SNAPSHOT_FILE = LOG_DIR / "regime_baseline_snapshot.json"

SYMBOL = os.getenv("REGIME_SYMBOL", "XAUUSD")
LOT = float(os.getenv("REGIME_LOT", "0.01"))
RUNTIME_SECONDS = int(os.getenv("REGIME_RUNTIME_SECONDS", "20"))
MIN_FREE_MARGIN_AFTER_ORDER = float(
    os.getenv("REGIME_MIN_FREE_MARGIN_AFTER_ORDER", "100.0")
)
MAX_PORTFOLIO_POSITIONS = 2

ACCOUNT = int(os.getenv("MT5_ACCOUNT", "0"))
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")
TERMINAL_PATH = os.getenv("MT5_PATH", "")

VB_MAGIC = int(os.getenv("REGIME_VB_MAGIC", "2026061502"))
MR_MAGIC = int(os.getenv("REGIME_MR_MAGIC", "2026061501"))

STRATEGY_PATHS = {
    "VB": REPO_ROOT / "mt5" / "2026" / "may" / "strategies" / "VB_H4_V1.py",
    "MR": BASE_DIR / "strategies" / "MR_M15_V1.py",
}

SUCCESS_RETCODES = {
    mt5.TRADE_RETCODE_DONE,
    mt5.TRADE_RETCODE_PLACED,
    mt5.TRADE_RETCODE_DONE_PARTIAL,
}


@dataclass(frozen=True)
class StrategySpec:
    name: str
    magic: int
    module: ModuleType


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_default(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "_asdict"):
        return value._asdict()
    return str(value)


def emit(event: str, **payload: Any) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {"time_utc": utc_now_iso(), "event": event, **payload}
    line = json.dumps(record, default=json_default, separators=(",", ":"))
    print(line, flush=True)
    with EVENT_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load strategy module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_strategies() -> dict[str, StrategySpec]:
    vb = load_module("regime_live_vb", STRATEGY_PATHS["VB"])
    mr = load_module("regime_live_mr", STRATEGY_PATHS["MR"])
    vb.PARAMETERS["SYMBOL"] = SYMBOL
    vb.PARAMETERS["LOT"] = LOT
    mr.PARAMETERS["SYMBOL"] = SYMBOL
    mr.PARAMETERS["LOT"] = LOT
    return {
        "VB": StrategySpec("VB", VB_MAGIC, vb),
        "MR": StrategySpec("MR", MR_MAGIC, mr),
    }


def state_file(dry_run: bool) -> Path:
    mode = "dry_run" if dry_run else "live"
    return LOG_DIR / f"regime_baseline_state_{mode}.json"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_signal_bar": {}, "last_managed_bar": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        state.setdefault("last_signal_bar", {})
        state.setdefault("last_managed_bar", {})
        return state
    except Exception as exc:
        emit("state_load_error", error=str(exc))
        return {"last_signal_bar": {}, "last_managed_bar": {}}


def save_state(state: dict[str, Any], path: Path) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def initialize_mt5(live: bool) -> None:
    if VB_MAGIC == MR_MAGIC:
        raise RuntimeError("REGIME_VB_MAGIC and REGIME_MR_MAGIC must be different")
    if not TERMINAL_PATH:
        raise RuntimeError("MT5_PATH is required")
    if not ACCOUNT or not PASSWORD or not SERVER:
        raise RuntimeError("MT5_ACCOUNT, MT5_PASSWORD, and MT5_SERVER are required")
    if not mt5.initialize(path=TERMINAL_PATH):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    if not mt5.login(ACCOUNT, PASSWORD, SERVER):
        raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")
    if not mt5.symbol_select(SYMBOL, True):
        raise RuntimeError(f"Cannot select symbol {SYMBOL}: {mt5.last_error()}")
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        raise RuntimeError(f"symbol_info failed: {mt5.last_error()}")
    volume_step = float(symbol_info.volume_step)
    normalized_steps = round(LOT / volume_step) if volume_step > 0.0 else 0
    normalized_lot = normalized_steps * volume_step
    if (
        LOT < float(symbol_info.volume_min)
        or LOT > float(symbol_info.volume_max)
        or volume_step <= 0.0
        or abs(normalized_lot - LOT) > 1e-9
    ):
        raise RuntimeError(
            f"REGIME_LOT={LOT} violates broker volume constraints: "
            f"min={symbol_info.volume_min}, max={symbol_info.volume_max}, "
            f"step={symbol_info.volume_step}"
        )
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"account_info failed: {mt5.last_error()}")
    if int(account.login) != ACCOUNT:
        raise RuntimeError(f"Connected account {account.login} does not match {ACCOUNT}")
    hedging_mode = getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", None)
    is_hedging = hedging_mode is not None and int(account.margin_mode) == int(
        hedging_mode
    )
    if live and not is_hedging:
        raise RuntimeError(
            "Live mode requires an MT5 hedging account so VB and MR can hold "
            "independent or opposite positions."
        )
    emit(
        "initialized",
        account=account.login,
        server=SERVER,
        symbol=SYMBOL,
        balance=account.balance,
        equity=account.equity,
        margin=account.margin,
        margin_free=account.margin_free,
        margin_mode=account.margin_mode,
        hedging_account=is_hedging,
        volume_min=symbol_info.volume_min,
        volume_max=symbol_info.volume_max,
        volume_step=symbol_info.volume_step,
    )


def strategy_for_magic(
    magic: int, strategies: dict[str, StrategySpec]
) -> str | None:
    for name, spec in strategies.items():
        if magic == spec.magic:
            return name
    return None


def position_payload(
    position: Any, strategies: dict[str, StrategySpec]
) -> dict[str, Any]:
    strategy = strategy_for_magic(int(getattr(position, "magic", 0)), strategies)
    side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
    return {
        "ticket": int(position.ticket),
        "strategy": strategy or "FOREIGN",
        "magic": int(getattr(position, "magic", 0)),
        "symbol": position.symbol,
        "side": side,
        "volume": float(position.volume),
        "entry_price": float(position.price_open),
        "current_price": float(position.price_current),
        "sl": float(position.sl or 0.0),
        "tp": float(position.tp or 0.0),
        "profit": float(position.profit),
        "time_utc": datetime.fromtimestamp(position.time, timezone.utc).isoformat(),
    }


def get_positions(strategies: dict[str, StrategySpec]) -> list[Any]:
    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError(f"positions_get failed: {mt5.last_error()}")
    return list(positions)


def validate_positions(
    positions: list[Any], strategies: dict[str, StrategySpec]
) -> tuple[dict[str, list[Any]], list[Any], list[str]]:
    owned = {name: [] for name in strategies}
    foreign = []
    violations = []
    for position in positions:
        name = (
            strategy_for_magic(int(getattr(position, "magic", 0)), strategies)
            if position.symbol == SYMBOL
            else None
        )
        if name is None:
            foreign.append(position)
        else:
            owned[name].append(position)
    for name, strategy_positions in owned.items():
        if len(strategy_positions) > 1:
            violations.append(f"{name} has {len(strategy_positions)} positions")
    if sum(len(value) for value in owned.values()) > MAX_PORTFOLIO_POSITIONS:
        violations.append("portfolio exceeds two owned positions")
    if foreign:
        violations.append(f"{len(foreign)} foreign account position(s) detected")
    return owned, foreign, violations


def account_snapshot(
    strategies: dict[str, StrategySpec],
    positions: list[Any],
    violations: list[str],
) -> dict[str, Any]:
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"account_info failed: {mt5.last_error()}")
    payload = {
        "time_utc": utc_now_iso(),
        "account": int(account.login),
        "symbol": SYMBOL,
        "balance": float(account.balance),
        "equity": float(account.equity),
        "margin": float(account.margin),
        "margin_free": float(account.margin_free),
        "margin_level": float(account.margin_level or 0.0),
        "position_count": len(positions),
        "positions": [position_payload(position, strategies) for position in positions],
        "violations": violations,
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, default=json_default), encoding="utf-8"
    )
    temporary.replace(SNAPSHOT_FILE)
    return payload


def latest_completed_row(spec: StrategySpec) -> tuple[pd.DataFrame, pd.Series] | None:
    frame = spec.module.get_data()
    if frame.empty or len(frame) < 3:
        emit("data_unavailable", strategy=spec.name, rows=len(frame))
        return None
    return frame, frame.iloc[-2]


def order_side(signal: str) -> int:
    return mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL


def calculate_order(
    spec: StrategySpec, signal: str, signal_row: pd.Series
) -> dict[str, Any] | None:
    tick = mt5.symbol_info_tick(SYMBOL)
    symbol_info = mt5.symbol_info(SYMBOL)
    if tick is None or symbol_info is None:
        emit("quote_unavailable", strategy=spec.name, error=str(mt5.last_error()))
        return None
    price = float(tick.ask if signal == "long" else tick.bid)
    atr = float(signal_row["atr"])
    if spec.name == "VB":
        sl_distance = float(spec.module.PARAMETERS["SL_ATR_MULTIPLIER"]) * atr
        tp = 0.0
    else:
        sl_distance = float(spec.module.PARAMETERS["SL_ATR_MULTIPLIER"]) * atr
        tp = float(signal_row["ema"])
        if (signal == "long" and tp <= price) or (signal == "short" and tp >= price):
            emit(
                "signal_rejected",
                strategy=spec.name,
                reason="ema_target_invalid_at_entry",
                signal=signal,
                price=price,
                tp=tp,
            )
            return None
    sl = price - sl_distance if signal == "long" else price + sl_distance
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT,
        "type": order_side(signal),
        "price": round(price, symbol_info.digits),
        "sl": round(sl, symbol_info.digits),
        "deviation": 50,
        "magic": spec.magic,
        "comment": f"REGIME_BASELINE_{spec.name}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if tp > 0.0:
        request["tp"] = round(tp, symbol_info.digits)
    margin = mt5.order_calc_margin(request["type"], SYMBOL, LOT, request["price"])
    if margin is None:
        emit(
            "margin_calculation_failed",
            strategy=spec.name,
            signal=signal,
            error=str(mt5.last_error()),
        )
        return None
    request["_required_margin"] = float(margin)
    return request


def preflight_order(
    request: dict[str, Any], reserved_margin: float = 0.0
) -> tuple[bool, dict[str, Any]]:
    account = mt5.account_info()
    if account is None:
        return False, {"reason": "account_info_failed", "error": mt5.last_error()}
    required_margin = float(request["_required_margin"])
    projected_free = float(account.margin_free) - reserved_margin - required_margin
    if projected_free < MIN_FREE_MARGIN_AFTER_ORDER:
        return False, {
            "reason": "minimum_free_margin",
            "required_margin": required_margin,
            "current_free_margin": float(account.margin_free),
            "cycle_reserved_margin": reserved_margin,
            "projected_free_margin": projected_free,
            "minimum_free_margin": MIN_FREE_MARGIN_AFTER_ORDER,
        }
    broker_request = {key: value for key, value in request.items() if not key.startswith("_")}
    check = mt5.order_check(broker_request)
    if check is None:
        return False, {"reason": "order_check_none", "error": mt5.last_error()}
    if int(check.retcode) != 0:
        return False, {
            "reason": "order_check_rejected",
            "retcode": int(check.retcode),
            "comment": str(check.comment),
            "required_margin": required_margin,
            "projected_free_margin": projected_free,
        }
    return True, {
        "required_margin": required_margin,
        "current_free_margin": float(account.margin_free),
        "cycle_reserved_margin": reserved_margin,
        "projected_free_margin": projected_free,
        "broker_check": check._asdict(),
    }


def submit_order(
    spec: StrategySpec,
    signal: str,
    signal_row: pd.Series,
    request: dict[str, Any],
    reservations: dict[str, float],
    dry_run: bool,
) -> bool:
    valid, preflight = preflight_order(request, reservations["margin"])
    common = {
        "strategy": spec.name,
        "signal": signal,
        "signal_bar_time": signal_row["time"],
        "request": request,
        "preflight": preflight,
    }
    if not valid:
        emit("order_blocked", **common)
        return False
    if dry_run:
        reservations["margin"] += float(request["_required_margin"])
        reservations["positions"] += 1.0
        emit("dry_run_order", **common)
        return True
    broker_request = {key: value for key, value in request.items() if not key.startswith("_")}
    result = mt5.order_send(broker_request)
    if result is None:
        emit("order_failed", **common, error=str(mt5.last_error()))
        return False
    success = int(result.retcode) in SUCCESS_RETCODES
    emit(
        "order_submitted" if success else "order_failed",
        **common,
        result=result._asdict(),
    )
    return success


def update_stop(position: Any, spec: StrategySpec, new_sl: float, dry_run: bool) -> bool:
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        return False
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": SYMBOL,
        "position": position.ticket,
        "sl": round(new_sl, symbol_info.digits),
        "tp": position.tp,
        "magic": spec.magic,
        "comment": f"REGIME_BASELINE_{spec.name}",
    }
    if dry_run:
        emit(
            "dry_run_stop_update",
            strategy=spec.name,
            ticket=position.ticket,
            old_sl=position.sl,
            new_sl=request["sl"],
        )
        return True
    result = mt5.order_send(request)
    success = result is not None and int(result.retcode) in SUCCESS_RETCODES
    emit(
        "stop_updated" if success else "stop_update_failed",
        strategy=spec.name,
        ticket=position.ticket,
        old_sl=position.sl,
        new_sl=request["sl"],
        result=result._asdict() if result is not None else None,
    )
    return success


def manage_vb(
    spec: StrategySpec, position: Any, frame: pd.DataFrame, dry_run: bool
) -> None:
    completed = frame.iloc[-2]
    active = frame[
        (frame["time"] >= pd.to_datetime(position.time, unit="s", utc=True))
        & (frame["time"] <= completed["time"])
    ]
    if active.empty:
        return
    old_sl = float(position.sl or 0.0)
    if old_sl <= 0.0:
        return
    if position.type == mt5.POSITION_TYPE_BUY:
        candidate = float(active["high"].max()) - float(
            spec.module.PARAMETERS["TRAIL_ATR_MULTIPLIER"]
        ) * float(completed["atr"])
        if candidate > old_sl:
            update_stop(position, spec, candidate, dry_run)
    else:
        candidate = float(active["low"].min()) + float(
            spec.module.PARAMETERS["TRAIL_ATR_MULTIPLIER"]
        ) * float(completed["atr"])
        if candidate < old_sl:
            update_stop(position, spec, candidate, dry_run)


def manage_mr(
    spec: StrategySpec, position: Any, completed: pd.Series, dry_run: bool
) -> None:
    entry = float(position.price_open)
    old_sl = float(position.sl or 0.0)
    tp = float(position.tp or 0.0)
    if old_sl <= 0.0 or tp <= 0.0:
        return
    side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
    if (side == "long" and old_sl >= entry) or (side == "short" and old_sl <= entry):
        return
    entry_atr = abs(entry - old_sl) / float(
        spec.module.PARAMETERS["SL_ATR_MULTIPLIER"]
    )
    retrace = (
        float(spec.module.PARAMETERS["BAND_ATR_MULTIPLIER"])
        * float(spec.module.PARAMETERS["BREAKEVEN_RETRACE_RATIO"])
        * entry_atr
    )
    trigger = tp - retrace if side == "long" else tp + retrace
    hit = (
        float(completed["high"]) >= trigger
        if side == "long"
        else float(completed["low"]) <= trigger
    )
    if hit:
        update_stop(position, spec, entry, dry_run)


def run_strategy_cycle(
    spec: StrategySpec,
    owned_positions: dict[str, list[Any]],
    violations: list[str],
    state: dict[str, Any],
    state_path: Path,
    reservations: dict[str, float],
    dry_run: bool,
) -> None:
    latest = latest_completed_row(spec)
    if latest is None:
        return
    frame, completed = latest
    completed_time = str(completed["time"])
    position = owned_positions[spec.name][0] if owned_positions[spec.name] else None

    if position is not None and state["last_managed_bar"].get(spec.name) != completed_time:
        if spec.name == "VB":
            manage_vb(spec, position, frame, dry_run)
        else:
            manage_mr(spec, position, completed, dry_run)
        state["last_managed_bar"][spec.name] = completed_time

    signal, reject_reason = spec.module.check_signal(completed)
    emit(
        "strategy_cycle",
        strategy=spec.name,
        signal_bar_time=completed["time"],
        signal=signal,
        reject_reason=reject_reason,
        has_position=position is not None,
    )
    if signal not in ("long", "short"):
        return
    if state["last_signal_bar"].get(spec.name) == completed_time:
        return
    state["last_signal_bar"][spec.name] = completed_time
    # Consume before the order attempt so a crash after broker acceptance
    # cannot repeat the same completed-bar signal.
    save_state(state, state_path)
    if violations:
        emit("signal_blocked", strategy=spec.name, signal=signal, reasons=violations)
        return
    if position is not None:
        emit(
            "signal_blocked",
            strategy=spec.name,
            signal=signal,
            reasons=["strategy already has one position"],
        )
        return
    owned_count = sum(len(value) for value in owned_positions.values()) + int(
        reservations["positions"]
    )
    if owned_count >= MAX_PORTFOLIO_POSITIONS:
        emit(
            "signal_blocked",
            strategy=spec.name,
            signal=signal,
            reasons=["portfolio already has two positions"],
        )
        return
    request = calculate_order(spec, signal, completed)
    if request is not None:
        submit_order(spec, signal, completed, request, reservations, dry_run)


def run_cycle(
    strategies: dict[str, StrategySpec],
    state: dict[str, Any],
    state_path: Path,
    dry_run: bool,
) -> None:
    positions = get_positions(strategies)
    owned, _, violations = validate_positions(positions, strategies)
    snapshot = account_snapshot(strategies, positions, violations)
    emit("account_snapshot", **snapshot)
    reservations = {"margin": 0.0, "positions": 0.0}
    for name in ("MR", "VB"):
        run_strategy_cycle(
            strategies[name],
            owned,
            violations,
            state,
            state_path,
            reservations,
            dry_run,
        )
        # Refresh before the next strategy so a live order consumes shared capacity.
        positions = get_positions(strategies)
        owned, _, violations = validate_positions(positions, strategies)
    save_state(state, state_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-account MT5 simulator/executor for VB + MR regime baseline"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow real order and stop-update requests. Default is dry-run.",
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.live
    strategies = load_strategies()
    state_path = state_file(dry_run)
    state = load_state(state_path)
    try:
        initialize_mt5(live=args.live)
        emit(
            "runner_started",
            mode="dry_run" if dry_run else "live",
            strategy_magics={name: spec.magic for name, spec in strategies.items()},
            maximum_positions_per_strategy=1,
            maximum_portfolio_positions=MAX_PORTFOLIO_POSITIONS,
            minimum_free_margin_after_order=MIN_FREE_MARGIN_AFTER_ORDER,
        )
        while True:
            try:
                run_cycle(strategies, state, state_path, dry_run)
            except Exception as exc:
                emit("cycle_error", error=str(exc))
            if args.once:
                break
            time.sleep(RUNTIME_SECONDS)
    except KeyboardInterrupt:
        emit("runner_stopped", reason="keyboard_interrupt")
    except Exception as exc:
        emit("fatal_error", error=str(exc))
        raise
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
