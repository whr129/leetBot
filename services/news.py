"""News service using RSS feeds."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Optional

import feedparser

logger = logging.getLogger("leetbot.news")

DEFAULT_FEEDS: dict[str, list[str]] = {
    "general": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    ],
    "tech": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
    ],
    "market": [
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    ],
}


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: Optional[str] = None
    summary: Optional[str] = None


class NewsService:
    """Async RSS feed parser for news headlines."""

    def __init__(self, feeds: Optional[dict[str, list[str]]] = None):
        self.feeds = feeds or DEFAULT_FEEDS

    def _parse_feed(self, url: str) -> list[dict]:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url)
            items = []
            for entry in feed.entries[:20]:
                pub = entry.get("published") or entry.get("updated", "")
                summary = entry.get("summary", "")
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                items.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "source": source,
                    "published": pub,
                    "summary": summary,
                })
            return items
        except Exception as e:
            logger.warning("Failed to parse feed %s: %s", url, e)
            return []

    async def _fetch_feed(self, url: str) -> list[dict]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._parse_feed, url))

    async def get_latest(
        self, category: Optional[str] = None, limit: int = 10,
    ) -> list[NewsItem]:
        if category and category in self.feeds:
            urls = self.feeds[category]
        else:
            urls = [u for cat_urls in self.feeds.values() for u in cat_urls]

        tasks = [self._fetch_feed(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: list[dict] = []
        for r in results:
            if isinstance(r, list):
                all_items.extend(r)

        all_items.sort(key=lambda x: x.get("published", ""), reverse=True)
        return [
            NewsItem(
                title=item["title"],
                link=item["link"],
                source=item["source"],
                published=item.get("published"),
                summary=item.get("summary"),
            )
            for item in all_items[:limit]
        ]

    async def get_market_news(self, limit: int = 10) -> list[NewsItem]:
        return await self.get_latest(category="market", limit=limit)

    async def search_news(self, keyword: str, limit: int = 10) -> list[NewsItem]:
        all_news = await self.get_latest(limit=100)
        keyword_lower = keyword.lower()
        matched = [
            item for item in all_news
            if keyword_lower in item.title.lower()
            or (item.summary and keyword_lower in item.summary.lower())
        ]
        return matched[:limit]
