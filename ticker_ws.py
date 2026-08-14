"""Binance WebSocket 行情客户端线程

- 单连接组合流推送所有自选交易对的 24h 行情
- 支持运行中动态增删订阅（SUBSCRIBE/UNSUBSCRIBE）
- 断线自动指数退避重连
"""
import json
import threading

import websocket

STREAM_TICKER = "wss://stream.binance.com:9443/stream"


class TickerStream(threading.Thread):
    RECONNECT_BASE = 3
    RECONNECT_MAX = 30

    def __init__(self, get_symbols, on_price, on_status, stop_event):
        super().__init__(daemon=True, name="TickerStream")
        self._get_symbols = get_symbols
        self._on_price = on_price
        self._on_status = on_status
        self._stop_event = stop_event
        self._lock = threading.Lock()
        self._want = set()
        self._subscribed = set()
        self._wake = threading.Event()

    def update(self, *_):
        """订阅列表可能变化时由主线程调用。"""
        with self._lock:
            self._want = {
                f"{s.strip().lower()}@ticker"
                for s in self._get_symbols()
                if s.strip()
            }
        self._wake.set()

    def run(self):
        backoff = self.RECONNECT_BASE
        while not self._stop_event.is_set():
            self.update()
            with self._lock:
                want = set(self._want)
            if not want:
                self._on_status("未选择币种")
                self._wake.clear()
                if self._stop_event.wait(1):
                    break
                continue

            url = f"{STREAM_TICKER}?streams={'/'.join(sorted(want))}"
            self._on_status("连接中…")
            try:
                ws = websocket.create_connection(
                    url, timeout=5, ping_interval=20, ping_timeout=10,
                )
            except Exception:
                self._on_status(f"重连 {backoff}s")
                if self._stop_event.wait(backoff):
                    break
                backoff = min(backoff * 2, self.RECONNECT_MAX)
                continue

            backoff = self.RECONNECT_BASE
            with self._lock:
                self._subscribed = set(want)
            self._on_status("已连接")
            try:
                self._loop(ws)
            except Exception:
                pass
            finally:
                try:
                    ws.close()
                except Exception:
                    pass
            self._on_status("连接断开")
            if self._stop_event.wait(backoff):
                break
            backoff = min(backoff * 2, self.RECONNECT_MAX)

    def _loop(self, ws):
        while not self._stop_event.is_set():
            self._reconcile(ws)
            try:
                message = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            if not message:
                continue
            self._handle(message)

    def _reconcile(self, ws):
        """根据最新自选列表动态订阅/退订。"""
        with self._lock:
            want = set(self._want)
        new = want - self._subscribed
        gone = self._subscribed - want
        if not new and not gone:
            return
        try:
            if new:
                ws.send(json.dumps({
                    "method": "SUBSCRIBE", "params": sorted(new), "id": 1,
                }))
            if gone:
                ws.send(json.dumps({
                    "method": "UNSUBSCRIBE", "params": sorted(gone), "id": 2,
                }))
        except Exception:
            pass
        with self._lock:
            self._subscribed = set(want)

    def _handle(self, message):
        try:
            payload = json.loads(message)
            data = payload.get("data")
            if not data:
                return
            symbol = data.get("s")
            price = data.get("c")
            if not symbol or price is None:
                return
            self._on_price(symbol, {
                "price": float(price),
                "pct": float(data.get("P") or 0),
                "volume": float(data.get("q") or 0),
            })
        except Exception:
            pass