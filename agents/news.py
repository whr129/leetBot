"""News curator specialist agent with isolated tools and memory."""

from dataclasses import asdict
from typing import Any, Optional

from openai import AsyncOpenAI

from agents.base import BaseAgent
from services.memory import AgentMemory
from services.news import NewsService

SYSTEM_PROMPT = """\
You are a news curator assistant in a Discord server.

You can fetch the latest headlines, market news, and search news by keyword \
using the tools provided. Always use tools to retrieve real data.

Guidelines:
- Be concise. Discord messages have a 2000-char limit.
- Present headlines as a numbered list with source attribution.
- Include links so users can read full articles.
- If the user has saved preferred topics, prioritize those in your responses.
- Use Markdown formatting for readability in Discord.
- Summarize objectively without editorializing.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_latest_news",
            "description": "Get the latest news headlines. Optionally filter by category (general, tech, market).",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["general", "tech", "market"],
                        "description": "News category to filter by",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of headlines to return (default 10)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_news",
            "description": "Get the latest stock market and finance news headlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of headlines (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search news headlines by keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Keyword to search for in headlines"},
                    "limit": {"type": "integer", "description": "Number of results (default 10)"},
                },
                "required": ["keyword"],
            },
        },
    },
]


class NewsAgent(BaseAgent):
    name = "news"
    system_prompt = SYSTEM_PROMPT
    tool_definitions = TOOL_DEFINITIONS

    def __init__(
        self,
        client: Optional[AsyncOpenAI],
        news_service: NewsService,
        model: str = "gpt-4o-mini",
        max_iterations: int = 8,
        memory_ttl_days: int = 7,
        memory_max_conversations: int = 50,
    ):
        memory = AgentMemory("news", ttl_days=memory_ttl_days, max_conversations=memory_max_conversations)
        super().__init__(client=client, memory=memory, model=model, max_iterations=max_iterations)
        self.news = news_service

    async def execute_tool(self, name: str, args: dict) -> Any:
        if name == "get_latest_news":
            items = await self.news.get_latest(
                category=args.get("category"),
                limit=args.get("limit", 10),
            )
            return [asdict(item) for item in items]

        if name == "get_market_news":
            items = await self.news.get_market_news(limit=args.get("limit", 10))
            return [asdict(item) for item in items]

        if name == "search_news":
            items = await self.news.search_news(
                keyword=args["keyword"],
                limit=args.get("limit", 10),
            )
            return [asdict(item) for item in items]

        return {"error": f"Unknown tool: {name}"}
