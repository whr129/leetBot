"""AI cog: /ask command with multi-agent routing."""

import discord
from discord.ext import commands

from bot.utils.embeds import error_embed

AGENT_COLORS = {
    "leetcode": discord.Color.green(),
    "stock": discord.Color.gold(),
    "news": discord.Color.blue(),
    "alerts": discord.Color.purple(),
}


class AICog(commands.Cog):
    """AI-powered assistance via multi-agent routing."""

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    def _get_router(self):
        return getattr(self.bot, "agent_router", None)

    @discord.slash_command(
        name="ask",
        description="Ask the AI anything (LeetCode, stocks, news, alerts...)",
    )
    async def ask(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, description="Your question or request"),
    ) -> None:
        await ctx.defer()

        router = self._get_router()
        if not router or not router.is_available():
            await ctx.respond(embed=error_embed("AI is not configured. Set OPENAI_API_KEY in .env"))
            return

        result = await router.run(query=question, discord_id=ctx.author.id)

        answer = result.answer
        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        footer_parts = [f"Agent: {result.agent_name}"]
        if result.tool_calls_made:
            tool_names = list(dict.fromkeys(tc["tool"] for tc in result.tool_calls_made))
            footer_parts.append(f"Tools: {', '.join(tool_names)}")
        footer_parts.append(f"Steps: {result.iterations}")

        color = AGENT_COLORS.get(result.agent_name, discord.Color.blurple())
        embed = discord.Embed(description=answer, color=color)
        embed.set_footer(text=" | ".join(footer_parts))
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    """Load the AI cog and initialize the multi-agent router."""
    from openai import AsyncOpenAI

    import config
    from agents.leetcode import LeetCodeAgent
    from agents.stock import StockAgent
    from agents.news import NewsAgent
    from agents.alerts import AlertAgent
    from agents.router import AgentRouter

    client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

    agents = {
        "leetcode": LeetCodeAgent(
            client=client,
            leetcode=bot.leetcode,
            model=config.AI_MODEL,
            max_iterations=config.AGENT_MAX_ITERATIONS,
            memory_ttl_days=config.MEMORY_TTL_DAYS,
            memory_max_conversations=config.MEMORY_MAX_CONVERSATIONS,
        ),
        "stock": StockAgent(
            client=client,
            stock_service=bot.stock_service,
            model=config.AI_MODEL,
            max_iterations=config.AGENT_MAX_ITERATIONS,
            memory_ttl_days=config.MEMORY_TTL_DAYS,
            memory_max_conversations=config.MEMORY_MAX_CONVERSATIONS,
        ),
        "news": NewsAgent(
            client=client,
            news_service=bot.news_service,
            model=config.AI_MODEL,
            max_iterations=config.AGENT_MAX_ITERATIONS,
            memory_ttl_days=config.MEMORY_TTL_DAYS,
            memory_max_conversations=config.MEMORY_MAX_CONVERSATIONS,
        ),
        "alerts": AlertAgent(
            client=client,
            alert_service=bot.alert_service,
            model=config.AI_MODEL,
            max_iterations=config.AGENT_MAX_ITERATIONS,
            memory_ttl_days=config.MEMORY_TTL_DAYS,
            memory_max_conversations=config.MEMORY_MAX_CONVERSATIONS,
        ),
    }

    bot.agent_router = AgentRouter(
        agents=agents,
        client=client,
        model=config.AI_MODEL,
    )
    bot.add_cog(AICog(bot))
