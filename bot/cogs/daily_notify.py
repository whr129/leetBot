"""Daily LeetCode challenge notification scheduler."""

import datetime
import html
import json
import logging
import re
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord.commands import SlashCommandGroup

import config
from bot.utils.embeds import daily_embed
from services.leetcode import LeetCodeAPIError

logger = logging.getLogger("leetbot.daily_notify")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_FILE = DATA_DIR / "notify_config.json"


def _strip_html(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", html.unescape(text))
    clean = clean.replace("\n", " ").strip()
    return clean[:max_len] + "..." if len(clean) > max_len else clean


class DailyNotifyCog(commands.Cog):
    """Scheduled daily LeetCode challenge notifications."""

    notify_group = SlashCommandGroup(
        "notify", "Daily LeetCode notification settings"
    )

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self._guild_configs: dict[int, dict] = {}
        self._load_config()

    def cog_unload(self) -> None:
        self._daily_check.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._daily_check.is_running():
            self._daily_check.start()

    def _load_config(self) -> None:
        if CONFIG_FILE.exists():
            try:
                raw = json.loads(CONFIG_FILE.read_text())
                self._guild_configs = {int(k): v for k, v in raw.items()}
                logger.info(
                    "Loaded daily-notify config for %d guild(s)",
                    len(self._guild_configs),
                )
            except Exception as exc:
                logger.warning("Failed to load notify config: %s", exc)

    def _save_config(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(
                {str(k): v for k, v in self._guild_configs.items()},
                indent=2,
            )
        )

    @tasks.loop(minutes=1)
    async def _daily_check(self) -> None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        for guild_id, cfg in list(self._guild_configs.items()):
            if not cfg.get("enabled"):
                continue
            hour = cfg.get("hour", config.DAILY_NOTIFY_HOUR)
            minute = cfg.get("minute", config.DAILY_NOTIFY_MINUTE)
            if now_utc.hour != hour or now_utc.minute != minute:
                continue
            last_sent = cfg.get("last_sent")
            today = now_utc.strftime("%Y-%m-%d")
            if last_sent == today:
                continue
            await self._send_daily(guild_id, cfg)
            cfg["last_sent"] = today
            self._save_config()

    @_daily_check.before_loop
    async def _before_daily_check(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_daily(self, guild_id: int, cfg: dict) -> None:
        channel_id = cfg.get("channel_id")
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logger.warning("Channel %s not found for guild %s", channel_id, guild_id)
            return
        try:
            challenge = await self.bot.leetcode.get_daily()
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

            url = (
                f"https://leetcode.com{link}"
                if link and not link.startswith("http")
                else link
            )
            embed = daily_embed(
                title=title,
                url=url or "https://leetcode.com",
                difficulty=difficulty,
                date=challenge.date,
                content=_strip_html(str(content)) if content else None,
                topic_tags=topic_tags,
            )
            if ac_rate is not None:
                embed.add_field(
                    name="Acceptance", value=f"{float(ac_rate):.1f}%", inline=True
                )
            await channel.send(
                content="**Daily LeetCode Challenge**", embed=embed
            )
            logger.info("Sent daily challenge to #%s in guild %s", channel.name, guild_id)
        except LeetCodeAPIError as e:
            logger.error("API error sending daily to guild %s: %s", guild_id, e)
        except Exception as e:
            logger.error("Error sending daily to guild %s: %s", guild_id, e)

    @notify_group.command(
        name="setup",
        description="Enable daily LeetCode challenge notifications in a channel",
    )
    @commands.has_permissions(manage_channels=True)
    async def setup(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(
            discord.TextChannel,
            description="Channel to post daily challenges in",
        ),
        hour: discord.Option(
            int,
            description="Hour to send (0-23, UTC). Default: 8",
            min_value=0,
            max_value=23,
            required=False,
        ) = None,
        minute: discord.Option(
            int,
            description="Minute to send (0-59, UTC). Default: 0",
            min_value=0,
            max_value=59,
            required=False,
        ) = None,
    ) -> None:
        """Set up daily challenge notifications for this server."""
        h = hour if hour is not None else config.DAILY_NOTIFY_HOUR
        m = minute if minute is not None else config.DAILY_NOTIFY_MINUTE
        self._guild_configs[ctx.guild_id] = {
            "channel_id": channel.id,
            "hour": h,
            "minute": m,
            "enabled": True,
            "last_sent": None,
        }
        self._save_config()
        embed = discord.Embed(
            title="Daily Notifications Enabled",
            description=(
                f"Daily LeetCode challenge will be posted in {channel.mention} "
                f"every day at **{h:02d}:{m:02d} UTC**."
            ),
            color=discord.Color.green(),
        )
        await ctx.respond(embed=embed)

    @notify_group.command(
        name="stop",
        description="Stop daily LeetCode challenge notifications",
    )
    @commands.has_permissions(manage_channels=True)
    async def stop(self, ctx: discord.ApplicationContext) -> None:
        """Disable daily challenge notifications for this server."""
        cfg = self._guild_configs.get(ctx.guild_id)
        if not cfg or not cfg.get("enabled"):
            await ctx.respond(
                embed=discord.Embed(
                    title="Not Active",
                    description="Daily notifications are not enabled for this server.",
                    color=discord.Color.orange(),
                )
            )
            return
        cfg["enabled"] = False
        self._save_config()
        await ctx.respond(
            embed=discord.Embed(
                title="Daily Notifications Disabled",
                description="Daily LeetCode challenge notifications have been stopped.",
                color=discord.Color.red(),
            )
        )

    @notify_group.command(
        name="status",
        description="Check daily notification settings for this server",
    )
    async def status(self, ctx: discord.ApplicationContext) -> None:
        """Show current notification configuration."""
        cfg = self._guild_configs.get(ctx.guild_id)
        if not cfg or not cfg.get("enabled"):
            await ctx.respond(
                embed=discord.Embed(
                    title="Daily Notifications",
                    description="Not configured for this server. Use `/notify setup` to enable.",
                    color=discord.Color.greyple(),
                )
            )
            return
        channel = self.bot.get_channel(cfg["channel_id"])
        ch_mention = channel.mention if channel else f"(unknown channel {cfg['channel_id']})"
        embed = discord.Embed(
            title="Daily Notifications",
            description="Active",
            color=discord.Color.green(),
        )
        embed.add_field(name="Channel", value=ch_mention, inline=True)
        embed.add_field(
            name="Time (UTC)",
            value=f"{cfg['hour']:02d}:{cfg['minute']:02d}",
            inline=True,
        )
        if cfg.get("last_sent"):
            embed.add_field(name="Last Sent", value=cfg["last_sent"], inline=True)
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    """Load the daily-notify cog."""
    bot.add_cog(DailyNotifyCog(bot))
