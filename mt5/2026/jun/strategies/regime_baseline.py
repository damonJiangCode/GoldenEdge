from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any

import MetaTrader5 as mt5  # type: ignore
import pandas as pd  # type: ignore
import requests  # type: ignore


STRATEGY_DIR = Path(__file__).resolve().parent
JUN_DIR = STRATEGY_DIR.parent
REPO_ROOT = STRATEGY_DIR.parents[3]
LOG_DIR = JUN_DIR / "logs"

METADATA = {
    "account": 60089392,
    "password": "Jwz990118.",
    "server": "TradeMaxGlobal-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_3\\terminal64.exe",
    "log_file": f"REGIME_BASELINE_{datetime.now().strftime('%m-%d__%H-%M')}.log",
    "title": "REGIME_BASELINE",
    "comment": "XAUUSD shared-account baseline: MR_M15_V1 + VB_H4_V1",
}

PARAMETERS = {
    "SYMBOL": "XAUUSD",
    "LOT": 0.01,
    "RUNTIME_SECONDS": 20,
    "MIN_FREE_MARGIN_AFTER_ORDER": 100.0,
    "MAX_PORTFOLIO_POSITIONS": 2,
    "VB_MAGIC": 2026061502,
    "MR_MAGIC": 2026061501,
}

TELEGRAM = {
    "BOT_TOKEN": "8221803362:AAGSmueTIdc5Ca_snea-gloHj1VQtPPSk8c",
    "CHAT_ID": "7262692073",
}

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / METADATA["log_file"]
STATE_FILE = LOG_DIR / f"{METADATA['title']}_state.json"

SYMBOL = PARAMETERS["SYMBOL"]
LOT = PARAMETERS["LOT"]
MIN_FREE_MARGIN_AFTER_ORDER = PARAMETERS["MIN_FREE_MARGIN_AFTER_ORDER"]
MAX_PORTFOLIO_POSITIONS = PARAMETERS["MAX_PORTFOLIO_POSITIONS"]
VB_MAGIC = PARAMETERS["VB_MAGIC"]
MR_MAGIC = PARAMETERS["MR_MAGIC"]

STRATEGY_PATHS = {
    "VB": REPO_ROOT / "mt5" / "2026" / "may" / "strategies" / "VB_H4_V1.py",
    "MR": STRATEGY_DIR / "MR_M15_V1.py",
}

@dataclass(frozen=True)
class StrategySpec:
    name: str
    magic: int
    module: ModuleType


def log_message(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as file:
            file.write(message + "\n")
    except Exception as exc:
        print(f"log_message() ERROR: {exc}")


def send_telegram_message(message: str) -> None:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM['BOT_TOKEN']}/sendMessage"
        payload = {"chat_id": TELEGRAM["CHAT_ID"], "text": message}
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            log_message(
                "send_telegram_message() failed: "
                f"{response.status_code} - {response.text}"
            )
    except Exception as exc:
        log_message(f"send_telegram_message() ERROR: {exc}")


def notify(message: str) -> None:
    print(message)
    log_message(message)
    send_telegram_message(message)


def log_local(message: str) -> None:
    print(message)
    log_message(message)


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
    # Child modules supply calculations only; the combined runner owns all output.
    vb.send_telegram_message = send_telegram_message
    vb.log_message = log_message
    mr.notify = notify
    mr.log_local = log_local
    return {
        "VB": StrategySpec("VB", VB_MAGIC, vb),
        "MR": StrategySpec("MR", MR_MAGIC, mr),
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_signal_bar": {}, "last_managed_bar": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        state.setdefault("last_signal_bar", {})
        state.setdefault("last_managed_bar", {})
        return state
    except Exception as exc:
        notify(f"❌ load_state() ERROR: {exc}")
        return {"last_signal_bar": {}, "last_managed_bar": {}}


def save_state(state: dict[str, Any], path: Path) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def initialize_mt5() -> bool:
    try:
        if VB_MAGIC == MR_MAGIC:
            raise RuntimeError("VB_MAGIC and MR_MAGIC must be different")
        if not mt5.initialize(METADATA["path"]):
            raise RuntimeError(
                f"❌ initialize_mt5(): Failed to initialize MT5: {mt5.last_error()}"
            )
        if not mt5.login(
            METADATA["account"], METADATA["password"], METADATA["server"]
        ):
            raise RuntimeError(
                f"❌ initialize_mt5(): Failed to log in MT5 account: {mt5.last_error()}"
            )
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"❌ initialize_mt5(): Failed to select symbol {SYMBOL}")
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
                f"LOT={LOT} violates broker volume constraints: "
                f"min={symbol_info.volume_min}, max={symbol_info.volume_max}, "
                f"step={symbol_info.volume_step}"
            )
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"account_info failed: {mt5.last_error()}")
        if int(account.login) != METADATA["account"]:
            raise RuntimeError(
                f"Connected account {account.login} does not match "
                f"{METADATA['account']}"
            )
        hedging_mode = getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", None)
        is_hedging = hedging_mode is not None and int(account.margin_mode) == int(
            hedging_mode
        )
        if not is_hedging:
            raise RuntimeError(
                "REGIME_BASELINE requires an MT5 hedging account so VB and MR can "
                "hold independent or opposite positions."
            )
        notify(
            "✅ MT5 initialized and logged in successfully\n"
            f"Account: {account.login}\n"
            f"Server: {METADATA['server']}\n"
            f"Strategy: {METADATA['title']}\n"
            f"Balance: ${account.balance:.2f}\n"
            f"Equity: ${account.equity:.2f}\n"
            f"Free Margin: ${account.margin_free:.2f}\n"
            "Position Limit: MR 1 + VB 1"
        )
        return True
    except Exception as exc:
        notify(f"❌ initialize_mt5() ERROR: {exc}")
        return False


def strategy_for_magic(
    magic: int, strategies: dict[str, StrategySpec]
) -> str | None:
    for name, spec in strategies.items():
        if magic == spec.magic:
            return name
    return None


def position_line(position: Any, strategies: dict[str, StrategySpec]) -> str:
    strategy = strategy_for_magic(int(getattr(position, "magic", 0)), strategies)
    side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
    return (
        f"{strategy or 'FOREIGN'}:{side}"
        f" TICKET:{int(position.ticket)}"
        f" LOT:{float(position.volume):.2f}"
        f" OPEN:{float(position.price_open):.2f}"
        f" CURRENT:{float(position.price_current):.2f}"
        f" SL:{float(position.sl or 0.0):.2f}"
        f" TP:{float(position.tp or 0.0):.2f}"
        f" PNL:{float(position.profit):.2f}"
    )


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


def log_account_status(
    strategies: dict[str, StrategySpec],
    positions: list[Any],
    violations: list[str],
) -> None:
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"account_info failed: {mt5.last_error()}")
    tick = mt5.symbol_info_tick(SYMBOL)
    timestamp = (
        datetime.fromtimestamp(tick.time, tz=timezone.utc)
        if tick is not None
        else datetime.now(timezone.utc)
    )
    timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"[{timestamp_text}] BALANCE:{account.balance:.2f}"
        f" EQUITY:{account.equity:.2f}"
        f" MARGIN:{account.margin:.2f}"
        f" FREE_MARGIN:{account.margin_free:.2f}"
        f" MARGIN_LEVEL:{float(account.margin_level or 0.0):.2f}%"
        f" POSITIONS:{len(positions)}"
    ]
    lines.extend(f"  ---  {position_line(position, strategies)}" for position in positions)
    if not positions:
        lines.append("  ---  POSITIONS:NONE")
    if violations:
        lines.append(f"  ---  VIOLATIONS:{', '.join(violations)}")
    log_message("\n".join(lines))


def latest_completed_row(spec: StrategySpec) -> tuple[pd.DataFrame, pd.Series] | None:
    frame = spec.module.get_data()
    if frame.empty or len(frame) < 3:
        notify(
            f"❌ run_{spec.name.lower()}(): get_data returned empty or "
            f"insufficient data ({len(frame)} rows)"
        )
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
        notify(
            f"❌ place_order(): {spec.name} symbol info or tick unavailable, "
            f"error: {mt5.last_error()}"
        )
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
            log_local(
                "⚠️ place_order(): MR skipped because EMA target is no longer valid\n"
                f"Signal bar: {signal_row['time']}\n"
                f"Direction: {signal}\n"
                f"Current price: {price:.2f}\n"
                f"Target EMA: {tp:.2f}"
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
        notify(
            f"❌ place_order(): {spec.name} margin calculation failed\n"
            f"Direction: {signal}\n"
            f"Error: {mt5.last_error()}"
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
) -> bool:
    valid, preflight = preflight_order(request, reservations["margin"])
    if not valid:
        notify(
            "⚠️ place_order(): blocked by shared-account margin check\n"
            f"Strategy: {spec.name}\n"
            f"Signal bar: {signal_row['time']}\n"
            f"Direction: {signal}\n"
            f"Reason: {preflight.get('reason')}\n"
            f"Required margin: ${float(preflight.get('required_margin', 0.0)):.2f}\n"
            f"Current free margin: ${float(preflight.get('current_free_margin', 0.0)):.2f}\n"
            f"Projected free margin: ${float(preflight.get('projected_free_margin', 0.0)):.2f}"
        )
        return False
    broker_request = {key: value for key, value in request.items() if not key.startswith("_")}
    result = mt5.order_send(broker_request)
    if result is None:
        notify(
            "❌ place_order(): Failed to place order: no return result\n"
            f"Strategy: {spec.name}\n"
            f"Signal bar: {signal_row['time']}\n"
            f"Direction: {signal}\n"
            f"Error: {mt5.last_error()}"
        )
        return False
    success = int(result.retcode) == mt5.TRADE_RETCODE_DONE
    notify(
        f"{'✅ Succeeded' if success else '❌ Failed'}\n"
        f"Strategy: {spec.name}\n"
        f"Signal bar: {signal_row['time']}\n"
        f"Order #: {getattr(result, 'order', 0)}\n"
        f"Direction: {'Buy' if signal == 'long' else 'Sell'}\n"
        f"Price: {float(request['price']):.2f}\n"
        f"SL: {float(request['sl']):.2f}\n"
        f"TP: {float(request.get('tp', 0.0)):.2f}\n"
        f"Required margin: ${float(request['_required_margin']):.2f}\n"
        f"Projected free margin: ${float(preflight['projected_free_margin']):.2f}\n"
        f"Result: {getattr(result, 'comment', 'unknown')} ({result.retcode})"
    )
    return success


def update_stop(position: Any, spec: StrategySpec, new_sl: float) -> bool:
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
    result = mt5.order_send(request)
    success = result is not None and int(result.retcode) == mt5.TRADE_RETCODE_DONE
    notify(
        f"{'✅ update_stop(): SL moved' if success else '❌ update_stop(): Failed'}\n"
        f"Strategy: {spec.name}\n"
        f"Ticket: {position.ticket}\n"
        f"Old SL: {float(position.sl or 0.0):.2f}\n"
        f"New SL: {float(request['sl']):.2f}\n"
        f"Result: {getattr(result, 'comment', 'no return')} "
        f"({getattr(result, 'retcode', None)})"
    )
    return success


def manage_vb(spec: StrategySpec, position: Any, frame: pd.DataFrame) -> None:
    completed = frame.iloc[-2]
    active = frame[
        frame["time"] >= pd.to_datetime(position.time, unit="s", utc=True)
    ]
    if active.empty:
        active = frame.tail(1)
    old_sl = float(position.sl or 0.0)
    if old_sl <= 0.0:
        return
    if position.type == mt5.POSITION_TYPE_BUY:
        candidate = float(active["high"].max()) - float(
            spec.module.PARAMETERS["TRAIL_ATR_MULTIPLIER"]
        ) * float(completed["atr"])
        if candidate > old_sl:
            update_stop(position, spec, candidate)
    else:
        candidate = float(active["low"].min()) + float(
            spec.module.PARAMETERS["TRAIL_ATR_MULTIPLIER"]
        ) * float(completed["atr"])
        if candidate < old_sl:
            update_stop(position, spec, candidate)


def manage_mr(spec: StrategySpec, position: Any, completed: pd.Series) -> None:
    entry = float(position.price_open)
    old_sl = float(position.sl or 0.0)
    tp = float(position.tp or 0.0)
    if old_sl <= 0.0 or tp <= 0.0:
        return
    side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
    position_bar_time = pd.to_datetime(position.time, unit="s", utc=True).floor(
        "15min"
    )
    if completed["time"] < position_bar_time:
        return
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        log_local(f"❌ update_breakeven(): {spec.name} symbol info unavailable")
        return
    tolerance = float(symbol_info.point) * 2.0
    if (side == "long" and old_sl >= entry - tolerance) or (
        side == "short" and old_sl <= entry + tolerance
    ):
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
        update_stop(position, spec, entry)


def log_strategy_cycle(
    spec: StrategySpec,
    frame: pd.DataFrame,
    completed: pd.Series,
    signal: str | None,
    reject_reason: str | None,
    position: Any | None,
) -> None:
    account = mt5.account_info()
    tick = mt5.symbol_info_tick(SYMBOL)
    timestamp = (
        datetime.fromtimestamp(tick.time, tz=timezone.utc)
        if tick is not None
        else datetime.now(timezone.utc)
    ).strftime("%Y-%m-%d %H:%M:%S")
    balance = float(account.balance) if account else 0.0
    equity = float(account.equity) if account else 0.0
    side = "none"
    if position is not None:
        side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
    if spec.name == "MR":
        message = (
            f"[{timestamp}] --- MR_M15_V1 ---"
            f" BALANCE:{balance:.2f} EQUITY:{equity:.2f}"
            f" POSITION:{side}"
            f" SIGNAL_BAR:{completed['time']}"
            f" CLOSE:{float(completed['close']):.2f}"
            f" EMA:{float(completed['ema']):.2f}"
            f" BAND:({float(completed['lower_band']):.2f},"
            f"{float(completed['upper_band']):.2f})"
            f" ATR:{float(completed['atr']):.2f}"
            f" ATR_RATIO:{float(completed['atr_ratio']):.2f}"
            f" H1_ADX:{float(completed['h1_adx']):.2f}"
            f" SIGNAL:{signal} REJECT:{reject_reason}"
        )
    else:
        current = frame.iloc[-1]
        message = (
            f"[{timestamp}] --- VB_H4_V1 ---"
            f" BALANCE:{balance:.2f} EQUITY:{equity:.2f}"
            f" POSITION:{side}"
            f" SIGNAL_BAR:{completed['time']}"
            f" CLOSE:({float(completed['close']):.2f},"
            f"{float(current['close']):.2f})"
            f" HIGH/LOW:({float(completed['high']):.2f},"
            f"{float(completed['low']):.2f})"
            f" DC_HIGH/LOW:({float(completed['donchian_high_n']):.2f},"
            f"{float(completed['donchian_low_n']):.2f})"
            f" EXIT_DC_HIGH/LOW:({float(completed['donchian_exit_high_m']):.2f},"
            f"{float(completed['donchian_exit_low_m']):.2f})"
            f" ATR:{float(completed['atr']):.2f}"
            f" ATR_RATIO:{float(completed['atr_ratio']):.2f}"
            f" H1_ADX:{float(completed['h1_adx']):.2f}"
            f" SIGNAL:{signal} REJECT:{reject_reason}"
        )
    print(f"[{timestamp}] --- {spec.module.METADATA['title']} --- ${balance:.2f}")
    log_message(message)


def run_strategy_cycle(
    spec: StrategySpec,
    owned_positions: dict[str, list[Any]],
    violations: list[str],
    state: dict[str, Any],
    state_path: Path,
    reservations: dict[str, float],
) -> None:
    latest = latest_completed_row(spec)
    if latest is None:
        return
    frame, completed = latest
    completed_time = str(completed["time"])
    position = owned_positions[spec.name][0] if owned_positions[spec.name] else None

    if position is not None and state["last_managed_bar"].get(spec.name) != completed_time:
        if spec.name == "VB":
            manage_vb(spec, position, frame)
        else:
            manage_mr(spec, position, completed)
        state["last_managed_bar"][spec.name] = completed_time

    signal, reject_reason = spec.module.check_signal(completed)
    log_strategy_cycle(spec, frame, completed, signal, reject_reason, position)
    if signal not in ("long", "short"):
        return
    if state["last_signal_bar"].get(spec.name) == completed_time:
        return
    state["last_signal_bar"][spec.name] = completed_time
    # Consume before the order attempt so a crash after broker acceptance
    # cannot repeat the same completed-bar signal.
    save_state(state, state_path)
    if violations:
        notify(
            f"⚠️ [{spec.name}] signal blocked\n"
            f"Signal bar: {completed['time']}\n"
            f"Direction: {signal}\n"
            f"Reason: {', '.join(violations)}"
        )
        return
    if position is not None:
        side = "long" if position.type == mt5.POSITION_TYPE_BUY else "short"
        notify(
            f"⚠️ [{spec.name}] already have open position ({side}), "
            f"skip new signal ({signal})"
        )
        return
    owned_count = sum(len(value) for value in owned_positions.values()) + int(
        reservations["positions"]
    )
    if owned_count >= MAX_PORTFOLIO_POSITIONS:
        notify(
            f"⚠️ [{spec.name}] portfolio already has two positions, "
            f"skip new signal ({signal})"
        )
        return
    request = calculate_order(spec, signal, completed)
    if request is not None:
        submit_order(spec, signal, completed, request, reservations)


def run_cycle(
    strategies: dict[str, StrategySpec],
    state: dict[str, Any],
    state_path: Path,
) -> None:
    positions = get_positions(strategies)
    owned, _, violations = validate_positions(positions, strategies)
    log_account_status(strategies, positions, violations)
    reservations = {"margin": 0.0, "positions": 0.0}
    for name in ("MR", "VB"):
        run_strategy_cycle(
            strategies[name],
            owned,
            violations,
            state,
            state_path,
            reservations,
        )
        # Refresh before the next strategy so a live order consumes shared capacity.
        positions = get_positions(strategies)
        owned, _, violations = validate_positions(positions, strategies)
    save_state(state, state_path)


def main() -> None:
    strategies = load_strategies()
    state_path = STATE_FILE
    state = load_state(state_path)
    try:
        if not initialize_mt5():
            notify("❌ main(): initialize_mt5() failed, exiting")
            return
        while True:
            try:
                run_cycle(strategies, state, state_path)
            except Exception as exc:
                notify(f"❌ run() ERROR: {exc}")
            time.sleep(PARAMETERS["RUNTIME_SECONDS"])
    except KeyboardInterrupt:
        notify("⏹️ KeyboardInterrupt: manual stop")
    except Exception as exc:
        notify(f"❌ main() ERROR: {exc}")
    finally:
        try:
            mt5.shutdown()
            notify("🔌 MT5 shutdown completed")
        except Exception:
            pass


if __name__ == "__main__":
    main()
