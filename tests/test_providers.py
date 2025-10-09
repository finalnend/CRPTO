from __future__ import annotations

from app.data.providers import BinanceRestProvider


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_provider_init_and_fetch_coingecko(monkeypatch):
    p = BinanceRestProvider(timeout_s=1)

    # Patch HTTP client GET for CoinGecko
    def fake_get(url, params=None):
        assert "coingecko" in url
        return _Resp({
            "bitcoin": {"usd": 1.0, "usd_24h_change": 0.1, "usd_24h_vol": 123.0},
        })

    monkeypatch.setattr(p, "_client", type("C", (), {"get": staticmethod(fake_get)})())

    out = p.fetch_from("coingecko", ["BTCUSDT"])  # smoke
    assert "BTCUSDT" in out

