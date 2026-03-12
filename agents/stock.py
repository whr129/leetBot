"""Stock market specialist agent with isolated tools and memory."""

from dataclasses import asdict
from typing import Any, Optional

from openai import AsyncOpenAI

from agents.base import BaseAgent
from services.memory import AgentMemory
from services.stock import StockService

SYSTEM_PROMPT = """\
You are a stock market analyst assistant in a Discord server.

You can look up stock quotes, daily summaries, market movers, and search for tickers \
using the tools provided. Always use tools to retrieve real data.

Guidelines:
- Be concise. Discord messages have a 2000-char limit.
- Include ticker symbol, price, and percentage change when discussing stocks.
- Format numbers with appropriate precision (prices to 2 decimals, percentages to 2 decimals).
- If the user has a saved watchlist, proactively reference it when relevant.
- Use Markdown formatting for readability in Discord.
- Do not provide financial advice; present data objectively.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get a real-time stock quote including price, change, and volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. 'AAPL'"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_summary",
            "description": "Get a detailed daily summary for a stock (open/high/low/close, market cap, P/E, 52-week range).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol"},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_movers",
            "description": "Get today's top stock gainers and losers among major companies.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_stock_symbol",
            "description": "Search for a stock ticker by company name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Company name or partial ticker to search"},
                },
                "required": ["query"],
            },
        },
    },
]


class StockAgent(BaseAgent):
    name = "stock"
    system_prompt = SYSTEM_PROMPT
    tool_definitions = TOOL_DEFINITIONS

    def __init__(
        self,
        client: Optional[AsyncOpenAI],
        stock_service: StockService,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
        memory_ttl_days: int = 7,
        memory_max_conversations: int = 50,
    ):
        memory = AgentMemory("stock", ttl_days=memory_ttl_days, max_conversations=memory_max_conversations)
        super().__init__(client=client, memory=memory, model=model, max_iterations=max_iterations)
        self.stock = stock_service

    async def execute_tool(self, name: str, args: dict) -> Any:
        if name == "get_stock_quote":
            quote = await self.stock.get_quote(args["symbol"])
            return asdict(quote)

        if name == "get_stock_summary":
            summary = await self.stock.get_daily_summary(args["symbol"])
            return asdict(summary)

        if name == "get_market_movers":
            return await self.stock.get_movers()

        if name == "search_stock_symbol":
            return await self.stock.search_symbol(args["query"])

        return {"error": f"Unknown tool: {name}"}
