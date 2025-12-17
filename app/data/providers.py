from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import httpx
import ssl


BINANCE_BASE = "https://api.binance.com"


@dataclass
class Ticker:
    symbol: str
    last: float
    change_pct: float
    volume: float
    ts: datetime
    high: float = 0.0
    low: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    quote_volume: float = 0.0


class BinanceRestProvider:
    def __init__(self, timeout_s: float = 5.0) -> None:
        self._client = httpx.Client(base_url=BINANCE_BASE, timeout=timeout_s, verify=self._make_ssl_context())
        self._lock = threading.Lock()

    def _normalize_symbol(self, s: str) -> str:
        s = s.replace("/", "").replace("-", "").replace(" ", "")
        return s.upper()

    def fetch(self, symbols: List[str]) -> Dict[str, Ticker]:
        norm = [self._normalize_symbol(s) for s in symbols]
        now = datetime.now()
        out: Dict[str, Ticker] = {}
        last_err: Exception | None = None
        for sym in norm:
            try:
                with self._lock:
                    r = self._client.get("/api/v3/ticker/24hr", params={"symbol": sym})
                r.raise_for_status()
                item = r.json()
                last = float(item.get("lastPrice") or item.get("prevClosePrice") or 0.0)
                change_pct = float(item.get("priceChangePercent", 0.0))
                volume = float(item.get("volume", 0.0))
                high = float(item.get("highPrice", 0.0))
                low = float(item.get("lowPrice", 0.0))
                bid = float(item.get("bidPrice", 0.0))
                ask = float(item.get("askPrice", 0.0))
                qvol = float(item.get("quoteVolume", 0.0))
                out[sym] = Ticker(sym, last, change_pct, volume, now, high=high, low=low, bid=bid, ask=ask, quote_volume=qvol)
            except Exception as e:
                last_err = e
                continue
        if not out and last_err:
            raise last_err
        return out

    def fetch_klines(self, symbol: str, interval: str = "1m", limit: int = 120) -> List[dict]:
        sym = self._normalize_symbol(symbol)
        with self._lock:
            r = self._client.get(
                "/api/v3/klines",
                params={"symbol": sym, "interval": interval, "limit": int(limit)},
            )
        r.raise_for_status()
        data = r.json()

        out: List[dict] = []
        for row in data or []:
            try:
                # https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
                open_time = int(row[0])
                open_ = float(row[1])
                high = float(row[2])
                low = float(row[3])
                close = float(row[4])
                volume = float(row[5])
                quote_volume = float(row[7]) if len(row) > 7 else 0.0
            except Exception:
                continue
            out.append(
                {
                    "symbol": sym,
                    "i": interval,
                    "t": open_time,
                    "o": open_,
                    "h": high,
                    "l": low,
                    "c": close,
                    "v": volume,
                    "q": quote_volume,
                    "x": True,
                }
            )
        return out

    def fetch_from(self, source: str, symbols: List[str]) -> Dict[str, Ticker]:
        source = source.lower()
        if source == "binance":
            return self.fetch(symbols)
        if source == "coingecko":
            return self._fetch_coingecko(symbols)
        if source == "coinbase":
            return self._fetch_coinbase(symbols)
        return self.fetch(symbols)

    def _fetch_coingecko(self, symbols: List[str]) -> Dict[str, Ticker]:
        mapping = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binancecoin",
        }
        ids = [mapping.get(self._normalize_symbol(s)) for s in symbols]
        ids = [i for i in ids if i]
        if not ids:
            return {}
        params = {
            "ids": ",".join(ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
        }
        with self._lock:
            r = self._client.get("https://api.coingecko.com/api/v3/simple/price", params=params)
        r.raise_for_status()
        data = r.json()
        now = datetime.now()
        out: Dict[str, Ticker] = {}
        reverse = {v: k for k, v in mapping.items()}
        for cid, obj in data.items():
            sym = reverse.get(cid)
            if not sym:
                continue
            last = float(obj.get("usd", 0.0))
            chg = float(obj.get("usd_24h_change", 0.0))
            vol_usd = float(obj.get("usd_24h_vol", 0.0))
            out[sym] = Ticker(sym, last, chg, 0.0, now, quote_volume=vol_usd)
        return out

    def _fetch_coinbase(self, symbols: List[str]) -> Dict[str, Ticker]:
        def to_product(sym: str) -> str | None:
            sym = self._normalize_symbol(sym)
            base = None
            if sym.endswith("USDT"):
                base = sym[:-4]
            elif sym.endswith("USD"):
                base = sym[:-3]
            if not base:
                return None
            return f"{base}-USD"

        out: Dict[str, Ticker] = {}
        now = datetime.now()
        last_err: Exception | None = None
        for s in symbols:
            pid = to_product(s)
            if not pid:
                continue
            try:
                with self._lock:
                    r1 = self._client.get(f"https://api.exchange.coinbase.com/products/{pid}/ticker")
                r1.raise_for_status()
                t = r1.json()
                price = float(t.get("price", 0.0))
                with self._lock:
                    r2 = self._client.get(f"https://api.exchange.coinbase.com/products/{pid}/stats")
                r2.raise_for_status()
                st = r2.json()
                last = float(st.get("last", price))
                open_ = float(st.get("open", last)) or last
                chg_pct = ((last - open_) / open_) * 100 if open_ else 0.0
                vol = float(st.get("volume", 0.0))
                high = float(st.get("high", 0.0))
                low = float(st.get("low", 0.0))
                bid = float(t.get("bid", 0.0))
                ask = float(t.get("ask", 0.0))
                qvol = last * vol if vol and last else 0.0
                sym = self._normalize_symbol(s)
                out[sym] = Ticker(sym, last, chg_pct, vol, now, high=high, low=low, bid=bid, ask=ask, quote_volume=qvol)
            except Exception as e:
                last_err = e
                continue
        if not out and last_err:
            raise last_err
        return out

    def _make_ssl_context(self):
        try:
            import truststore  # type: ignore
            return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:
            try:
                return ssl.create_default_context()
            except Exception:
                try:
                    import certifi  # type: ignore
                    return ssl.create_default_context(cafile=certifi.where())
                except Exception:
                    return ssl.create_default_context()

