"""News slash commands."""

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.utils.embeds import error_embed


class NewsCog(commands.Cog):
    """News headline commands."""

    news_group = SlashCommandGroup("news", "News commands")

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.news = bot.news_service

    def _news_embed(self, items, title: str) -> discord.Embed:
        lines = []
        for i, item in enumerate(items[:10], 1):
            source = f" ({item.source})" if item.source else ""
            lines.append(f"**{i}.** [{item.title}]({item.link}){source}")
        embed = discord.Embed(
            title=title,
            description="\n".join(lines) or "No articles found.",
            color=discord.Color.blue(),
        )
        return embed

    @news_group.command(name="latest", description="Get the latest news headlines")
    async def latest(
        self,
        ctx: discord.ApplicationContext,
        category: discord.Option(
            str,
            description="News category",
            choices=[
                discord.OptionChoice("General", "general"),
                discord.OptionChoice("Tech", "tech"),
                discord.OptionChoice("Market", "market"),
            ],
            required=False,
        ) = None,
    ) -> None:
        await ctx.defer()
        try:
            items = await self.news.get_latest(category=category, limit=10)
            title = f"Latest {category.title() if category else ''} News".strip()
            await ctx.respond(embed=self._news_embed(items, title))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch news: {e}"))

    @news_group.command(name="market", description="Get the latest market/finance news")
    async def market(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()
        try:
            items = await self.news.get_market_news(limit=10)
            await ctx.respond(embed=self._news_embed(items, "Market News"))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch market news: {e}"))


def setup(bot: discord.Bot) -> None:
    from services.news import NewsService
    bot.news_service = NewsService()
    bot.add_cog(NewsCog(bot))
