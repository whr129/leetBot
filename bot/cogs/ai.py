"""AI cog: single /ask command powered by the ReAct agent."""

import discord
from discord.ext import commands

from bot.utils.embeds import error_embed


class AICog(commands.Cog):
    """AI-powered LeetCode assistance via ReAct agent."""

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    def _get_agent(self):
        return getattr(self.bot, "react_agent", None)

    @discord.slash_command(name="ask", description="Ask the AI anything about LeetCode (search, explain, suggest, stats...)")
    async def ask(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, description="Your question or request"),
    ) -> None:
        await ctx.defer()

        agent = self._get_agent()
        if not agent or not agent.is_available():
            await ctx.respond(embed=error_embed("AI is not configured. Set OPENAI_API_KEY in .env"))
            return

        result = await agent.run(
            user_message=question,
            discord_id=ctx.author.id,
        )

        answer = result.answer
        if len(answer) > 1900:
            answer = answer[:1900] + "..."

        footer_parts = []
        if result.tool_calls_made:
            tool_names = list(dict.fromkeys(tc["tool"] for tc in result.tool_calls_made))
            footer_parts.append(f"Tools: {', '.join(tool_names)}")
        footer_parts.append(f"Steps: {result.iterations}")

        embed = discord.Embed(
            description=answer,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=" | ".join(footer_parts))
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    """Load the AI cog and initialize the ReAct agent."""
    from services.ai import ReActAgent
    from services.tools import ToolExecutor
    import config

    notify_cog = bot.cogs.get("DailyNotifyCog")
    executor = ToolExecutor(leetcode=bot.leetcode, notify_cog=notify_cog)
    bot.react_agent = ReActAgent(
        api_key=config.OPENAI_API_KEY,
        tool_executor=executor,
        model=config.AI_MODEL,
        max_iterations=config.AGENT_MAX_ITERATIONS,
    )
    bot.add_cog(AICog(bot))
