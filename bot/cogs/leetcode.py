"""LeetCode commands: daily, problem, random, stats."""

import html
import re
from typing import Optional

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.utils.embeds import daily_embed, error_embed, problem_embed, user_stats_embed
from services.leetcode import LeetCodeAPIError, LeetCodeService


def strip_html(text: str, max_len: int = 500) -> str:
    """Strip HTML and truncate."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", html.unescape(text))
    clean = clean.replace("\n", " ").strip()
    return clean[:max_len] + "..." if len(clean) > max_len else clean


class LeetCodeCog(commands.Cog):
    """LeetCode-related slash commands."""

    leetcode_group = SlashCommandGroup("leetcode", "LeetCode problem commands")

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leetcode: LeetCodeService = bot.leetcode

    @leetcode_group.command(name="daily", description="Get today's LeetCode daily challenge")
    async def daily(self, ctx: discord.ApplicationContext) -> None:
        """Fetch and display today's daily challenge."""
        await ctx.defer()
        try:
            challenge = await self.leetcode.get_daily()
            q = challenge.question
            if isinstance(q, dict):
                title = q.get("title", "Daily Challenge")
                link = challenge.link or q.get("link", "")
                difficulty = q.get("difficulty", "Unknown")
                content = q.get("content")
                topic_tags = q.get("topicTags", q.get("topic_tags", []))
                ac_rate = q.get("acRate")
            else:
                title = getattr(q, "title", "Daily Challenge")
                link = challenge.link
                difficulty = getattr(q, "difficulty", "Unknown")
                content = getattr(q, "content", None)
                topic_tags = getattr(q, "topicTags", []) or getattr(q, "topic_tags", [])
                ac_rate = getattr(q, "acRate", None)

            url = f"https://leetcode.com{link}" if link and not link.startswith("http") else link
            embed = daily_embed(
                title=title,
                url=url or "https://leetcode.com",
                difficulty=difficulty,
                date=challenge.date,
                content=strip_html(str(content)) if content else None,
                topic_tags=topic_tags,
            )
            if ac_rate is not None:
                embed.add_field(name="Acceptance", value=f"{float(ac_rate):.1f}%", inline=True)
            await ctx.respond(embed=embed)
        except LeetCodeAPIError as e:
            await ctx.respond(embed=error_embed(str(e)))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch daily: {e}"))

    @leetcode_group.command(name="problem", description="Look up a LeetCode problem by ID or slug")
    async def problem(
        self,
        ctx: discord.ApplicationContext,
        query: discord.Option(str, description="Problem ID or slug (e.g. 1, two-sum)"),
    ) -> None:
        """Look up a problem by ID or slug."""
        await ctx.defer()
        try:
            prob = await self.leetcode.get_problem(query)
            embed = problem_embed(
                title=prob.title,
                url=prob.url,
                difficulty=prob.difficulty,
                frontend_id=prob.frontend_id,
                topic_tags=prob.topic_tags,
                content=strip_html(prob.content) if prob.content else None,
                ac_rate=prob.ac_rate,
            )
            await ctx.respond(embed=embed)
        except LeetCodeAPIError as e:
            await ctx.respond(embed=error_embed(str(e)))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch problem: {e}"))

    @leetcode_group.command(name="random", description="Get a random LeetCode problem")
    async def random(
        self,
        ctx: discord.ApplicationContext,
        difficulty: discord.Option(
            str,
            description="Filter by difficulty",
            choices=[discord.OptionChoice("Easy", "Easy"), discord.OptionChoice("Medium", "Medium"), discord.OptionChoice("Hard", "Hard")],
            required=False,
        ) = None,
        topic: discord.Option(str, description="Topic tag slug (e.g. dynamic-programming)", required=False) = None,
    ) -> None:
        """Get a random problem with optional filters."""
        await ctx.defer()
        try:
            prob = await self.leetcode.get_random_problem(difficulty=difficulty, tag=topic)
            embed = problem_embed(
                title=prob.title,
                url=prob.url,
                difficulty=prob.difficulty,
                frontend_id=prob.frontend_id,
                topic_tags=prob.topic_tags,
                content=strip_html(prob.content) if prob.content else None,
                ac_rate=prob.ac_rate,
            )
            await ctx.respond(embed=embed)
        except LeetCodeAPIError as e:
            await ctx.respond(embed=error_embed(str(e)))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch random problem: {e}"))

    @leetcode_group.command(name="stats", description="Get a user's LeetCode profile stats")
    async def stats(
        self,
        ctx: discord.ApplicationContext,
        username: discord.Option(str, description="LeetCode username"),
    ) -> None:
        """Get LeetCode user stats."""
        await ctx.defer()
        name = username
        try:
            profile = await self.leetcode.get_user_profile(name)
            embed = user_stats_embed(
                username=profile.username,
                total_solved=profile.total_solved,
                easy_solved=profile.easy_solved,
                medium_solved=profile.medium_solved,
                hard_solved=profile.hard_solved,
                acceptance_rate=profile.acceptance_rate,
                ranking=profile.ranking,
            )
            await ctx.respond(embed=embed)
        except LeetCodeAPIError as e:
            await ctx.respond(embed=error_embed(str(e)))
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Failed to fetch stats: {e}"))


def setup(bot: discord.Bot) -> None:
    """Load the LeetCode cog."""
    bot.add_cog(LeetCodeCog(bot))
