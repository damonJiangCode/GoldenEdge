from datetime import timedelta, datetime, time as dtime
import time
import pandas as pd
import MetaTrader5 as mt5
import talib
import requests
import os

# ==== 设置日志目录和文件 ====
LOG_DIR = "../logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR, f"m15_stop_trend_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
)

# ==== 设置 MT5 账户信息 ====
ACCOUNT = 10006696600
PASSWORD = "G*XhQg0j"
SERVER = "MetaQuotes-Demo"
MT5_PATH = r"C:\\Program Files\\MetaTrader 5 Account3\\terminal64.exe"
RET_CODE_MESSAGES = {
    mt5.TRADE_RETCODE_DONE: "交易成功",
    mt5.TRADE_RETCODE_REQUOTE: "重新报价",
    mt5.TRADE_RETCODE_REJECT: "请求被拒绝",
    mt5.TRADE_RETCODE_CANCEL: "请求被取消",
    mt5.TRADE_RETCODE_PLACED: "已成功下单",
    mt5.TRADE_RETCODE_DONE_PARTIAL: "部分成交",
    mt5.TRADE_RETCODE_ERROR: "通用错误",
    mt5.TRADE_RETCODE_TIMEOUT: "请求超时",
    mt5.TRADE_RETCODE_INVALID: "无效请求",
    mt5.TRADE_RETCODE_INVALID_VOLUME: "无效手数",
    mt5.TRADE_RETCODE_INVALID_PRICE: "无效价格",
    mt5.TRADE_RETCODE_INVALID_STOPS: "止盈/止损无效",
    mt5.TRADE_RETCODE_NO_MONEY: "余额不足",
    mt5.TRADE_RETCODE_PRICE_CHANGED: "价格已变动",
    mt5.TRADE_RETCODE_PRICE_OFF: "无报价",
    mt5.TRADE_RETCODE_INVALID_EXPIRATION: "无效过期时间",
    mt5.TRADE_RETCODE_ORDER_CHANGED: "订单状态已改变",
    mt5.TRADE_RETCODE_TOO_MANY_REQUESTS: "请求过多",
}

# ==== 每日总结 ====
sent_morning_balance = None
sent_evening_balance = None

# ==== 设置 Telegram Bot 信息 ====
TELEGRAM_BOT_TOKEN = "8147556168:AAGX-4T7T9LKtxhhsBFjJzM6JHkCAJ-HnDQ"
TELEGRAM_CHAT_ID = "7262692073"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
# === telegram 状态 ===
last_update_id = -1
is_mt5_trading_enabled = True

# ==== 设置交易参数 ====
SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
LOT = 0.01

# ==== 设置指标参数 ====
RSI_PERIOD = 14
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35
ATR_PERIOD = 14
BB_PERIOD = 20
TP_MULTIPLIER = 2.0
SL_MULTIPLIER = 1.0


# ==== 日志打印 ====
def log_message(message: str):
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        print(f"❌ log_message 异常: {e}")


# ==== Telegram 消息发送 ====
def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            message = f"❌ Telegram 发送失败：{response.status_code} - {response.text}"
            print(message)
            log_message(message)
    except Exception as e:
        message = f"❌ send_telegram_message 异常: {e}"
        print(message)
        log_message(message)


# ==== 初始化 Telegram ====
def init_last_update_id():
    global last_update_id
    try:
        response = requests.get(f"{TELEGRAM_API}/getUpdates", timeout=10)
        data = response.json()
        if data["ok"] and data["result"]:
            last_update_id = data["result"][-1]["update_id"]
    except Exception as e:
        print(f"初始化 last_update_id 失败: {e}")
        log_message(f"初始化 last_update_id 失败: {e}")


# === telegram 指令处理 ===
def check_telegram_command():
    try:
        global last_update_id
        global is_mt5_trading_enabled
        response = requests.get(f"{TELEGRAM_API}/getUpdates", timeout=10)
        data = response.json()
        if not data["ok"] or not data["result"]:
            return
        latest = data["result"][-1]
        update_id = latest["update_id"]
        if update_id == last_update_id:
            return
        last_update_id = update_id
        message = latest.get("message", {})
        text = message.get("text", "").strip().lower()
        sender_id = str(message.get("chat", {}).get("id"))
        if sender_id != TELEGRAM_CHAT_ID:
            return
        if text == "run":
            if is_mt5_trading_enabled:
                message = "⚠️ 算法交易已启用"
                print(message)
                log_message(message)
                send_telegram_message(message)
            else:
                is_mt5_trading_enabled = True
                message = "✅ 开始启动算法交易"
                print(message)
                log_message(message)
                send_telegram_message(message)
        elif text == "stop":
            if is_mt5_trading_enabled:
                is_mt5_trading_enabled = False
                message = "🛑 开始关闭算法交易"
                print(message)
                log_message(message)
                send_telegram_message(message)
            else:
                message = "⚠️ 算法交易已关闭"
                print(message)
                log_message(message)
                send_telegram_message(message)
        elif text == "balance":
            account_info = mt5.account_info()  # type: ignore
            if account_info is None:
                message = "❌ 获取账户信息失败"
                print(message)
                log_message(message)
                send_telegram_message(message)
            else:
                balance = account_info.balance
                message = f"💰 当前账户余额: {balance}"
                print(message)
                log_message(message)
                send_telegram_message(message)
        else:
            return
    except Exception as e:
        message = f"❌ check_telegram_command 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 初始化 MT5 ====
def initialize_mt5():
    try:
        if not mt5.initialize(path=MT5_PATH):  # type: ignore
            raise RuntimeError("❌ MT5 初始化失败")
        if not mt5.login(ACCOUNT, PASSWORD, SERVER):  # type: ignore
            raise RuntimeError("❌ MT5 登录失败")
    except Exception as e:
        message = f"❌ initialize_mt5 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 获取数据并计算指标 ====
def get_data(bars=1000):
    try:
        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, bars)  # type: ignore
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df["rsi"] = talib.RSI(df["close"], timeperiod=RSI_PERIOD)  # type: ignore
        df["atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=ATR_PERIOD)  # type: ignore
        upper, middle, lower = talib.BBANDS(
            df["close"], timeperiod=BB_PERIOD, nbdevup=2, nbdevdn=2, matype=0  # type: ignore
        )
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["bb_diff"] = upper - lower
        return df.dropna()
    except Exception as e:
        message = f"❌ get_data 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)
        return pd.DataFrame()  # 返回空DataFrame防止主流程崩溃


# ==== 检查是否接近市场收盘时间 ====
def is_close_to_market_close():
    try:
        now = datetime.now().time()
        if dtime(14, 58, 30) <= now <= dtime(14, 59, 30):
            print("接近市场收盘时间")
            log_message("接近市场收盘时间")
            send_telegram_message("接近市场收盘时间")
            return True
        return False
    except Exception as e:
        message = f"❌ is_close_to_market_close 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)
        return False


# ==== 检查是否有仓位 ====
def has_positions():
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions is None:
            print("⚠️ 查询仓位失败")
            log_message("⚠️ 查询仓位失败")
            send_telegram_message("⚠️ 查询仓位失败")
            return None

        if len(positions) == 0:
            return None

        pos = positions[0]  # 只用来判断放方向
        direction = "long" if pos.type == mt5.POSITION_TYPE_BUY else "short"
        return direction
    except Exception as e:
        message = f"❌ has_positions 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 平仓 ====
def close_all_positions():
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions is None or len(positions) == 0:
            message = "⚠️ 尝试平仓，但无仓可平"
            print(message)
            log_message(message)
            send_telegram_message(message)
            return

        symbol_info = mt5.symbol_info(SYMBOL)  # type: ignore
        if symbol_info is None:
            message = f"❌ 获取 {SYMBOL} 信息失败，无法平仓"
            print(message)
            log_message(message)
            send_telegram_message(message)
            return

        for position in positions:
            opposite_order_type = (
                mt5.ORDER_TYPE_SELL
                if position.type == mt5.POSITION_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )

            tick = mt5.symbol_info_tick(SYMBOL)  # type: ignore
            if tick is None:
                message = "❌ 获取报价失败，跳过当前持仓"
                print(message)
                log_message(message)
                send_telegram_message(message)
                continue

            price = tick.bid if opposite_order_type == mt5.ORDER_TYPE_SELL else tick.ask
            digits = symbol_info.digits
            price = round(price, digits)

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": SYMBOL,
                "volume": position.volume,
                "type": opposite_order_type,
                "position": position.ticket,
                "price": price,
                "deviation": 50,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(close_request)  # type: ignore

            if result is None:
                message = f"❌ 平仓失败：无返回结果\n单号: {position.ticket}"
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                ret_msg = RET_CODE_MESSAGES.get(result.retcode, "未知错误")
                message = f"❌ 平仓失败\n" f"结果: {ret_msg} ({result.retcode})\n"
            else:
                message = f"✅ 平仓成功\n" f"结果: 成功 ({result.retcode})"

            print(message)
            log_message(message)
            send_telegram_message(message)
    except Exception as e:
        message = f"❌ close_all_positions 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 动态更新 SL/TP ====
def update_sl_tp_dynamic():
    try:
        positions = mt5.positions_get(symbol=SYMBOL)  # type: ignore
        if positions is None or len(positions) == 0:
            return

        symbol_info = mt5.symbol_info(SYMBOL)  # type: ignore
        if symbol_info is None:
            message = f"❌ 获取 {SYMBOL} 信息失败，无法更新止盈止损"
            print(message)
            log_message(message)
            send_telegram_message(message)
            return
        digits = symbol_info.digits

        atr = get_data(bars=1000).iloc[-1]["atr"]

        for pos in positions:
            ticket = pos.ticket
            order_type = pos.type
            entry_price = pos.price_open

            new_sl = (
                entry_price - SL_MULTIPLIER * atr
                if order_type == mt5.POSITION_TYPE_BUY
                else entry_price + SL_MULTIPLIER * atr
            )

            new_tp = round(
                entry_price + TP_MULTIPLIER * atr
                if order_type == mt5.POSITION_TYPE_BUY
                else entry_price - TP_MULTIPLIER * atr
            )

            if pos.sl == new_sl and pos.tp == new_tp:
                continue

            modify_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": round(new_sl, digits),
                "tp": round(new_tp, digits),
                "symbol": SYMBOL,
            }

            result = mt5.order_send(modify_request)  # type: ignore

            if result is None:
                message = f"❌ 更新止盈止损失败：无返回结果\n单号: {pos.ticket}"
            elif result.retcode != mt5.TRADE_RETCODE_DONE:
                ret_msg = RET_CODE_MESSAGES.get(result.retcode, "未知错误")
                message = (
                    f"❌ 更新止盈止损失败\n" f"结果: {ret_msg} ({result.retcode})\n"
                )
            else:
                message = f"✅ 更新止盈止损成功\n" f"结果: 成功 ({result.retcode})"
            print(message)
            log_message(message)
            return
    except Exception as e:
        message = f"❌ update_sl_tp_dynamic 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 检查交易信号 ====
def check_signal(df):
    try:

        if has_positions():
            current_direction = has_positions()
            if current_direction == 'long' and df.iloc[-2]['close'] < df.iloc[-2]['open']:
                message = f"⚠️ 已有 {current_direction} 仓位, 出现阴线, 平仓"
                print(message)
                log_message(message)
                send_telegram_message(message)
                close_all_positions()
            elif current_direction == 'short' and df.iloc[-2]['close'] > df.iloc[-2]['open']:
                message = f"⚠️ 已有 {current_direction} 仓位, 出现阳线, 平仓"
                print(message)
                log_message(message)
                send_telegram_message(message)
                close_all_positions()    
            return None

        # RSI 信号
        rsi_up = df.iloc[-3]["rsi"] < df.iloc[-2]["rsi"] < df.iloc[-1]["rsi"]
        rsi_down = df.iloc[-3]["rsi"] > df.iloc[-2]["rsi"] > df.iloc[-1]["rsi"]
        rsi_overbought_trend = (
            df.iloc[-2]["rsi"] >= RSI_OVERBOUGHT and df.iloc[-1]["rsi"] >= RSI_OVERBOUGHT
        )
        rsi_oversold_trend = (
            df.iloc[-2]["rsi"] <= RSI_OVERSOLD and df.iloc[-1]["rsi"] <= RSI_OVERSOLD
        )
        rsi_signal = 'long' if rsi_up and rsi_overbought_trend else 'short' if rsi_down and rsi_oversold_trend else None

        # BB 信号
        bb_open = (
            df.iloc[-1]["bb_diff"] > df.iloc[-2]["bb_diff"] > df.iloc[-3]["bb_diff"]
        )
        bb_signal = True if bb_open else None

        # 信号核对
        signal = rsi_signal if rsi_signal and bb_signal else None

        return signal
    except Exception as e:
        message = f"❌ check_signal 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 下单逻辑 ====
def place_order(signal, atr):
    try:
        tick = mt5.symbol_info_tick(SYMBOL)  # type: ignore
        if tick is None:
            message = "❌ 获取报价失败，无法下单"
            print(message)
            log_message(message)
            send_telegram_message(message)
            return

        symbol_info = mt5.symbol_info(SYMBOL)  # type: ignore
        if symbol_info is None:
            message = f"❌ 获取 {SYMBOL} 信息失败，无法下单"
            print(message)
            log_message(message)
            send_telegram_message(message)
            return

        price = tick.ask if signal == "long" else tick.bid
        digits = symbol_info.digits
        sl = (
            price - SL_MULTIPLIER * atr
            if signal == "long"
            else price + SL_MULTIPLIER * atr
        )
        tp = (
            price + TP_MULTIPLIER * atr
            if signal == "long"
            else price - TP_MULTIPLIER * atr
        )
        order_type = mt5.ORDER_TYPE_BUY if signal == "long" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": LOT,
            "type": order_type,
            "price": round(price, digits),
            "sl": round(sl, digits),
            "tp": round(tp, digits),
            "deviation": 50,
            "comment": "M15-RSI-BB-PLAN-A",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)  # type: ignore

        if result is None:
            message = "❌ 下单失败：返回结果为 None"
        elif hasattr(result, "retcode"):
            retcode_msg = RET_CODE_MESSAGES.get(result.retcode, "未知错误")
            message = (
                f"订单: {'✅ 成功' if result.retcode == mt5.TRADE_RETCODE_DONE else '❌ 失败'}\n"
                f"方向：{'买' if signal == 'long' else '卖'}\n"
                f"价格: {price:.2f}\n"
                f"止损: {sl:.2f}\n"
                f"止盈: {tp:.2f}\n"
                f"结果: {retcode_msg} ({result.retcode})\n"
            )
        else:
            message = f"❌ 下单失败：未知返回格式 {result}"

        print(message)
        log_message(message)
        send_telegram_message(message)
    except Exception as e:
        message = f"❌ place_order 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 余额报告 ====
def check_and_send_daily_balance_report():
    try:
        global sent_morning_balance, sent_evening_balance

        now = datetime.now()
        today = now.date()
        current_time = now.time()

        # 发送早报
        if dtime(6, 0, 0) <= current_time < dtime(6, 0, 40):
            if sent_morning_balance != today:
                account_info = mt5.account_info()  # type: ignore
                if account_info is None:
                    message = "❌ 余额获取失败"
                    print(message)
                    log_message(message)
                    send_telegram_message(message)
                    return

                balance = account_info.balance
                equity = account_info.equity

                message = f"🌅\n" f"余额: {balance:.2f}\n" f"净值: {equity:.2f}"
                print(message)
                log_message(message)
                send_telegram_message(message)
                sent_morning_balance = today

        # 发送晚报
        if dtime(21, 0, 0) <= current_time < dtime(21, 0, 40):
            if sent_evening_balance != today:
                account_info = mt5.account_info()  # type: ignore
                if account_info is None:
                    message = "❌ 余额获取失败"
                    print(message)
                    log_message(message)
                    send_telegram_message(message)
                    return

                balance = account_info.balance
                equity = account_info.equity

                message = f"🌙\n" f"余额: {balance:.2f}\n" f"净值: {equity:.2f}"
                print(message)
                log_message(message)
                send_telegram_message(message)
                sent_evening_balance = today
        return
    except Exception as e:
        message = f"❌ check_and_send_daily_balance_report 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 每次运行策略 ====
def run():
    try:
        check_telegram_command()
        check_and_send_daily_balance_report()
        if is_close_to_market_close():
            direction = has_positions()
            if direction:
                max_attempts = 3  # 防止无限循环
                attempt = 0
                while attempt < max_attempts and has_positions():
                    close_all_positions()
                    attempt += 1

        # update_sl_tp_dynamic()

        df = get_data()
        signal = check_signal(df)

        timestamp = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        message = f"[{timestamp}] ACC_BALNC: {mt5.account_info().balance}  |  RSI[-1]: {df.iloc[-1]['rsi']:.2f} - RSI[-2]: {df.iloc[-2]['rsi']:.2f} - RSI[-3]: {df.iloc[-3]['rsi']:.2f}  |  BB_DIFF[-1]: {df.iloc[-1]['bb_diff']:.2f} - BB_DIFF[-2]: {df.iloc[-2]['bb_diff']:.2f} - BB_DIFF[-3]: {df.iloc[-3]['bb_diff']:.2f}  |  ATR: {df.iloc[-1]['atr']:.2f}"  # type: ignore
        print(message)
        log_message(message)

        if signal:
            if not is_mt5_trading_enabled:
                message = f"✅ 检测到交易信号: {signal}"
                print(message)
                log_message(message)
                send_telegram_message(message)

                message = "⚠️ MT5交易已禁用, 无法下单"
                print(message)
                log_message(message)
                send_telegram_message(message)
                return

            atr = df.iloc[-1]["atr"]
            place_order(signal, atr)
    except Exception as e:
        message = f"❌ run 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


# ==== 主函数 ====
def main():
    try:
        init_last_update_id()
        initialize_mt5()
        while True:
            run()
            time.sleep(60)
    except Exception as e:
        message = f"❌ main 异常: {e}"
        print(message)
        log_message(message)
        send_telegram_message(message)


if __name__ == "__main__":
    main()
    mt5.shutdown()  # type: ignore