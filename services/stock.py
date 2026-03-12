"""Stock market data service using yfinance."""

import asyncio
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any, Optional

import yfinance as yf

logger = logging.getLogger("leetbot.stock")


@dataclass
class StockQuote:
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None
    currency: str = "USD"


@dataclass
class StockSummary:
    symbol: str
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    prev_close: float
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None


class StockService:
    """Async wrapper around yfinance for stock data."""

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    def _get_info(self, symbol: str) -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        return ticker.info

    async def get_quote(self, symbol: str) -> StockQuote:
        info = await self._run_sync(self._get_info, symbol.upper())
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev = info.get("previousClose", info.get("regularMarketPreviousClose", price))
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0
        return StockQuote(
            symbol=info.get("symbol", symbol.upper()),
            name=info.get("shortName", info.get("longName", symbol.upper())),
            price=round(price, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=info.get("volume", info.get("regularMarketVolume", 0)) or 0,
            market_cap=info.get("marketCap"),
            currency=info.get("currency", "USD"),
        )

    async def get_daily_summary(self, symbol: str) -> StockSummary:
        info = await self._run_sync(self._get_info, symbol.upper())
        return StockSummary(
            symbol=info.get("symbol", symbol.upper()),
            name=info.get("shortName", info.get("longName", symbol.upper())),
            open=info.get("open", info.get("regularMarketOpen", 0)) or 0,
            high=info.get("dayHigh", info.get("regularMarketDayHigh", 0)) or 0,
            low=info.get("dayLow", info.get("regularMarketDayLow", 0)) or 0,
            close=info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0,
            volume=info.get("volume", info.get("regularMarketVolume", 0)) or 0,
            prev_close=info.get("previousClose", info.get("regularMarketPreviousClose", 0)) or 0,
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        )

    def _get_movers_sync(self) -> dict[str, list[dict]]:
        symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "BRK-B", "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "PG",
        ]
        results = []
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                info = t.info
                price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
                prev = info.get("previousClose", price)
                if not prev:
                    continue
                change_pct = (price - prev) / prev * 100
                results.append({
                    "symbol": sym,
                    "name": info.get("shortName", sym),
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                })
            except Exception:
                continue
        return {
            "gainers": sorted(results, key=lambda x: x["change_pct"], reverse=True)[:5],
            "losers": sorted(results, key=lambda x: x["change_pct"])[:5],
        }

    async def get_movers(self) -> dict[str, list[dict]]:
        return await self._run_sync(self._get_movers_sync)

    async def search_symbol(self, query: str) -> list[dict]:
        def _search(q: str) -> list[dict]:
            try:
                results = yf.Tickers(q)
                return [{"symbol": s, "name": s} for s in results.symbols[:10]]
            except Exception:
                ticker = yf.Ticker(q)
                info = ticker.info
                if info.get("symbol"):
                    return [{"symbol": info["symbol"], "name": info.get("shortName", q)}]
                return []
        return await self._run_sync(_search, query.upper())

    async def get_price(self, symbol: str) -> Optional[float]:
        """Quick price check for alert comparison."""
        try:
            info = await self._run_sync(self._get_info, symbol.upper())
            return info.get("currentPrice") or info.get("regularMarketPrice")
        except Exception:
            return None
