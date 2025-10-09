from __future__ import annotations

import json
from typing import List

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtWebSockets import QWebSocket


class BinanceWsClient(QObject):
    tick = Signal(dict)
    error = Signal(str)
    connectedChanged = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._ws = QWebSocket()
        self._symbols: List[str] = []
        self._wire()

    def _wire(self) -> None:
        self._ws.connected.connect(lambda: self.connectedChanged.emit(True))
        self._ws.disconnected.connect(lambda: self.connectedChanged.emit(False))
        self._ws.textMessageReceived.connect(self._on_msg)
        self._ws.errorOccurred.connect(lambda e: self.error.emit(str(e)))

    def start(self, symbols: List[str]) -> None:
        syms = [s.replace("/", "").replace("-", "").replace(" ", "").lower() for s in symbols]
        self._symbols = syms
        streams = "/".join(f"{s}@ticker" for s in syms)
        url = f"wss://stream.binance.com:9443/stream?streams={streams}"
        try:
            self._ws.close()
        except Exception:
            pass
        self._ws.open(QUrl(url))

    def stop(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass

    def set_symbols(self, symbols: List[str]) -> None:
        if [s.lower() for s in symbols] != self._symbols:
            self.start(symbols)

    def _on_msg(self, msg: str) -> None:
        try:
            obj = json.loads(msg)
            data = obj.get("data") or obj
            s = (data.get("s") or data.get("symbol") or "").upper()
            last = float(data.get("c") or data.get("lastPrice") or 0.0)
            chg = float(data.get("P") or data.get("priceChangePercent") or 0.0)
            vol = float(data.get("v") or data.get("volume") or 0.0)
            high = float(data.get("h") or 0.0)
            low = float(data.get("l") or 0.0)
            bid = float(data.get("b") or 0.0)
            ask = float(data.get("a") or 0.0)
            qvol = float(data.get("q") or 0.0)
            now = data.get("E")  # event time might exist; UI formats ts itself
            packed = {
                s: {
                    "symbol": s,
                    "last": last,
                    "change_pct": chg,
                    "volume": vol,
                    "high": high,
                    "low": low,
                    "bid": bid,
                    "ask": ask,
                    "quote_volume": qvol,
                    "ts": now,
                }
            }
            self.tick.emit(packed)
        except Exception as e:
            self.error.emit(str(e))


class BinanceKlineWsClient(QObject):
    kline = Signal(dict)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._ws = QWebSocket()
        self._ws.textMessageReceived.connect(self._on_msg)
        self._ws.errorOccurred.connect(lambda e: self.error.emit(str(e)))

    def start(self, symbol: str, interval: str = "1m") -> None:
        s = symbol.replace("/", "").replace("-", "").replace(" ", "").lower()
        url = f"wss://stream.binance.com:9443/ws/{s}@kline_{interval}"
        try:
            self._ws.close()
        except Exception:
            pass
        self._ws.open(QUrl(url))

    def stop(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass

    def _on_msg(self, msg: str) -> None:
        try:
            o = json.loads(msg)
            k = o.get("k") or {}
            d = {
                "symbol": (o.get("s") or k.get("s") or "").upper(),
                "t": int(k.get("t", 0)),
                "o": float(k.get("o", 0.0)),
                "h": float(k.get("h", 0.0)),
                "l": float(k.get("l", 0.0)),
                "c": float(k.get("c", 0.0)),
                "v": float(k.get("v", 0.0)),
                "q": float(k.get("q", 0.0)),
                "x": bool(k.get("x", False)),
            }
            self.kline.emit(d)
        except Exception as e:
            self.error.emit(str(e))

