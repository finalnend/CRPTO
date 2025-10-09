from __future__ import annotations

from app.ws.binance import BinanceWsClient, BinanceKlineWsClient


class _StubWS:
    def __init__(self):
        self.last_url = None
        class S:
            def connect(self, *a, **k):
                pass
        self.connected = S(); self.disconnected = S(); self.textMessageReceived = S(); self.errorOccurred = S()
    def close(self):
        pass
    def open(self, url):
        self.last_url = url


def test_ws_client_builds_url(monkeypatch):
    c = BinanceWsClient()
    monkeypatch.setattr(c, "_ws", _StubWS())
    c.start(["BTCUSDT", "ETHUSDT"])
    stub = c._ws
    assert stub.last_url is not None


def test_kline_client_builds_url(monkeypatch):
    c = BinanceKlineWsClient()
    monkeypatch.setattr(c, "_ws", _StubWS())
    c.start("BTCUSDT", "1m")
    assert c._ws.last_url is not None

