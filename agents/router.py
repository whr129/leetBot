"""Agent router - dispatches /ask queries to the correct specialist agent."""

import logging
import re
from typing import Optional

from openai import AsyncOpenAI

from agents.base import AgentResult, BaseAgent

logger = logging.getLogger("leetbot.router")

STOCK_KEYWORDS = {
    "stock", "stocks", "share", "shares", "ticker", "market", "price",
    "quote", "portfolio", "bull", "bear", "earnings", "dividend",
    "s&p", "nasdaq", "dow", "nyse", "ipo", "etf", "trading",
    "gainers", "losers", "movers",
}

STOCK_PATTERN = re.compile(
    r"\$[A-Z]{1,5}\b|(?<!\w)[A-Z]{1,5}(?:\.[A-Z])?\b(?=.*(?:stock|price|quote|buy|sell|market))",
    re.IGNORECASE,
)

NEWS_KEYWORDS = {
    "news", "headline", "headlines", "briefing", "breaking", "article",
    "report", "journalism", "press", "media", "current events",
    "what happened", "what's happening", "latest",
}

ALERT_KEYWORDS = {
    "alert", "alerts", "remind", "reminder", "reminders", "due date",
    "deadline", "notify me", "notification", "set alert", "price alert",
    "watch", "track",
}


class AgentRouter:
    """Routes user queries to the correct specialist agent."""

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4o-mini",
        default_agent: str = "leetcode",
    ):
        self.agents = agents
        self.client = client
        self.model = model
        self.default_agent = default_agent

    def is_available(self) -> bool:
        return any(a.is_available() for a in self.agents.values())

    def _keyword_route(self, query: str) -> Optional[str]:
        lower = query.lower()
        words = set(lower.split())

        alert_score = len(words & ALERT_KEYWORDS)
        if any(phrase in lower for phrase in ("remind me", "notify me", "set alert", "due date", "price alert")):
            alert_score += 2
        if alert_score >= 1:
            return "alerts"

        stock_score = len(words & STOCK_KEYWORDS)
        if STOCK_PATTERN.search(query):
            stock_score += 2
        if stock_score >= 1:
            return "stock"

        news_score = len(words & NEWS_KEYWORDS)
        if any(phrase in lower for phrase in ("what's happening", "what happened", "current events")):
            news_score += 2
        if news_score >= 1:
            return "news"

        return None

    async def _llm_route(self, query: str) -> str:
        if not self.client:
            return self.default_agent
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the user query into exactly one category. "
                            "Reply with ONLY one word: leetcode, stock, news, or alerts.\n"
                            "- leetcode: coding problems, algorithms, data structures, LeetCode\n"
                            "- stock: stock prices, market data, tickers, financial instruments\n"
                            "- news: current events, headlines, articles, briefings\n"
                            "- alerts: reminders, price alerts, notifications, due dates, tracking"
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=10,
                temperature=0,
            )
            category = resp.choices[0].message.content.strip().lower()
            if category in self.agents:
                return category
        except Exception as e:
            logger.warning("LLM routing failed: %s", e)
        return self.default_agent

    async def route(self, query: str) -> str:
        agent_name = self._keyword_route(query)
        if agent_name and agent_name in self.agents:
            return agent_name
        return await self._llm_route(query)

    async def run(
        self,
        query: str,
        discord_id: Optional[int] = None,
    ) -> AgentResult:
        agent_name = await self.route(query)
        agent = self.agents[agent_name]
        logger.info("Routing to %s agent", agent_name)
        return await agent.run(user_message=query, discord_id=discord_id)
