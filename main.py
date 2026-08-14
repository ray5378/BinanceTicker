"""BinanceTicker - 系统托盘实时币价

Windows 托盘图标悬停显示自选币种实时行情（价格/24h涨跌/成交量），
右键菜单可动态增删自选币种。
"""
import re
import sys
import threading
import time

import pystray
from PIL import Image, ImageDraw, ImageFont
from pystray import Menu, MenuItem

import config
from ticker_ws import TickerStream

POLL_INTERVAL = 1.0
TOOLTIP_MAX = 120

prices = {}
prices_lock = threading.Lock()
status = "启动中…"
status_lock = threading.Lock()
stop_event = threading.Event()
stream = None
icon_ref = None


# ---------------------------------------------------------------------------
# 行情格式化
# ---------------------------------------------------------------------------

def fmt_price(value):
    if value is None:
        return "-"
    if value >= 1000:
        dec = 2
    elif value >= 10:
        dec = 3
    elif value >= 1:
        dec = 4
    elif value >= 0.01:
        dec = 6
    else:
        dec = 8
    s = f"{value:,.{dec}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_volume(value):
    if value is None:
        return "-"
    if value >= 1e9:
        return f"{value / 1e9:.2f}B"
    if value >= 1e6:
        return f"{value / 1e6:.2f}M"
    if value >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:.0f}"


def line_for(symbol, data):
    if not data:
        return f"{symbol}: …"
    arrow = "\u25b2" if data.get("pct", 0) >= 0 else "\u25bc"
    return (
        f"{symbol}  {fmt_price(data.get('price'))} "
        f"{arrow}{abs(data.get('pct', 0)):.2f}%  "
        f"vol {fmt_volume(data.get('volume'))}"
    )


def build_summary(symbols, limit=None):
    with prices_lock:
        snapshot = {s: dict(prices.get(s, {})) for s in symbols}
    lines = [line_for(s, snapshot.get(s)) for s in symbols]
    text = "\n".join(lines)
    if limit and len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


# ---------------------------------------------------------------------------
# 回调
# ---------------------------------------------------------------------------

def on_price(symbol, data):
    with prices_lock:
        prices[symbol] = data


def on_status(text):
    global status
    with status_lock:
        status = text
    try:
        if icon_ref is not None:
            icon_ref.update_menu()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 托盘图标
# ---------------------------------------------------------------------------

def make_icon():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = 3
    d.ellipse((m, m, size - m, size - m),
              fill=(240, 205, 110, 255), outline=(150, 110, 20, 255), width=3)
    ring = size * 0.60
    t = (size - ring) / 2
    d.ellipse((t, t, size - t, size - t),
              outline=(180, 140, 40, 255), width=3)
    try:
        font = ImageFont.truetype("arialbd.ttf", int(size * 0.42))
    except Exception:
        font = ImageFont.load_default()
    text = "B"
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1]),
           text, font=font, fill=(90, 60, 10, 255))
    return img


# ---------------------------------------------------------------------------
# 菜单
# ---------------------------------------------------------------------------

def _get_symbols():
    return config.load_symbols()


def is_selected(symbol):
    return lambda item: symbol in set(_get_symbols())


def toggle_symbol(symbol):
    def action(icon, item):
        symbols = _get_symbols()
        if symbol in symbols:
            symbols = [s for s in symbols if s != symbol]
        else:
            symbols.append(symbol)
        config.save_symbols(symbols)
        stream.update()
        icon.update_menu()
    return action


def menu_symbols(icon=None):
    selected = set(_get_symbols())
    union = sorted(set(config.PRESET_SYMBOLS) | selected,
                   key=lambda s: (s not in selected, s))
    items = [MenuItem(s, toggle_symbol(s), checked=is_selected(s))
             for s in union]
    return items


def prompt_add(icon, item):
    try:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        answer = simpledialog.askstring(
            "添加币种", "输入交易对，如 BTCUSDT 或 BTC", parent=root)
        root.destroy()
    except Exception:
        answer = None
    if not answer:
        return
    symbol = re.sub(r"[^A-Za-z0-9]", "", answer).upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", symbol):
        return
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"
    symbols = _get_symbols()
    if symbol not in symbols:
        symbols.append(symbol)
        config.save_symbols(symbols)
        stream.update()
    icon.update_menu()


def show_popup(icon, item):
    try:
        icon.notify(build_summary(_get_symbols()),
                    "BinanceTicker 实时行情")
    except Exception:
        pass


def do_quit(icon, item):
    stop_event.set()
    if stream is not None:
        stream.update()
    icon.stop()


def menu_factory():
    with status_lock:
        st = status
    return [
        MenuItem("查看行情", show_popup, default=True),
        Menu.SEPARATOR,
        MenuItem("自选币种", Menu(menu_symbols)),
        MenuItem("添加币种…", prompt_add),
        Menu.SEPARATOR,
        MenuItem(f"状态: {st}", None, enabled=False),
        Menu.SEPARATOR,
        MenuItem("退出", do_quit),
    ]


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def updater_loop(icon):
    last_summary = None
    while not stop_event.is_set():
        summary = build_summary(_get_symbols(), limit=TOOLTIP_MAX)
        if summary != last_summary:
            last_summary = summary
            try:
                icon.title = summary
            except Exception:
                pass
        time.sleep(POLL_INTERVAL)


def main():
    global stream, icon_ref
    selftest = "--selftest" in sys.argv
    stop_event.clear()
    stream = TickerStream(_get_symbols, on_price, on_status, stop_event)
    stream.update()
    stream.start()

    icon = pystray.Icon("BinanceTicker", make_icon(),
                        "BinanceTicker 启动中…", menu=Menu(menu_factory))
    icon_ref = icon

    if selftest:
        def _selftest():
            time.sleep(6)
            # 触发菜单重建，验证 checked 回调无异常
            icon.update_menu()
            time.sleep(1)
            stop_event.set()
            icon.stop()
        threading.Thread(target=_selftest, daemon=True).start()

    threading.Thread(target=updater_loop, args=(icon,), daemon=True).start()
    icon.run()
    if selftest:
        print("SELFTEST OK")


if __name__ == "__main__":
    main()