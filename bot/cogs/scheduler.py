"""Consolidated scheduler: daily LeetCode, news briefing, alert checks, memory cleanup."""

import datetime
import html
import json
import logging
import re
from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord.commands import SlashCommandGroup

import config
from bot.utils.embeds import daily_embed
from services.leetcode import LeetCodeAPIError

logger = logging.getLogger("leetbot.scheduler")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SCHEDULE_CONFIG = DATA_DIR / "schedule_config.json"


def _strip_html(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", html.unescape(text))
    clean = clean.replace("\n", " ").strip()
    return clean[:max_len] + "..." if len(clean) > max_len else clean


class SchedulerCog(commands.Cog):
    """All scheduled tasks: daily LeetCode, news briefing, alert checks."""

    schedule_group = SlashCommandGroup("schedule", "Scheduled notification settings")

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self._guild_configs: dict[int, dict] = {}
        self._load_config()

    def cog_unload(self) -> None:
        self._minute_tick.cancel()
        self._alert_check.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._minute_tick.is_running():
            self._minute_tick.start()
        if not self._alert_check.is_running():
            self._alert_check.start()

    def _load_config(self) -> None:
        if SCHEDULE_CONFIG.exists():
            try:
                raw = json.loads(SCHEDULE_CONFIG.read_text())
                self._guild_configs = {int(k): v for k, v in raw.items()}
                logger.info("Loaded schedule config for %d guild(s)", len(self._guild_configs))
            except Exception as exc:
                logger.warning("Failed to load schedule config: %s", exc)
        old_config = DATA_DIR / "notify_config.json"
        if old_config.exists() and not self._guild_configs:
            try:
                raw = json.loads(old_config.read_text())
                for k, v in raw.items():
                    self._guild_configs[int(k)] = {
                        "leetcode_channel": v.get("channel_id"),
                        "leetcode_hour": v.get("hour", config.DAILY_NOTIFY_HOUR),
                        "leetcode_minute": v.get("minute", config.DAILY_NOTIFY_MINUTE),
                        "leetcode_enabled": v.get("enabled", False),
                        "leetcode_last_sent": v.get("last_sent"),
                        "news_channel": None,
                        "news_hour": 7,
                        "news_minute": 0,
                        "news_enabled": False,
                        "news_last_sent": None,
                    }
                self._save_config()
                logger.info("Migrated old notify_config.json to schedule_config.json")
            except Exception as exc:
                logger.warning("Failed to migrate old config: %s", exc)

    def _save_config(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SCHEDULE_CONFIG.write_text(
            json.dumps({str(k): v for k, v in self._guild_configs.items()}, indent=2)
        )

    # -- Minute tick: daily LeetCode + news briefing ---------------------------

    @tasks.loop(minutes=1)
    async def _minute_tick(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.strftime("%Y-%m-%d")
        for guild_id, cfg in list(self._guild_configs.items()):
            if cfg.get("leetcode_enabled") and cfg.get("leetcode_channel"):
                if now.hour == cfg.get("leetcode_hour") and now.minute == cfg.get("leetcode_minute"):
                    if cfg.get("leetcode_last_sent") != today:
                        await self._send_daily_leetcode(guild_id, cfg)
                        cfg["leetcode_last_sent"] = today
                        self._save_config()

            if cfg.get("news_enabled") and cfg.get("news_channel"):
                if now.hour == cfg.get("news_hour") and now.minute == cfg.get("news_minute"):
                    if cfg.get("news_last_sent") != today:
                        await self._send_news_briefing(guild_id, cfg)
                        cfg["news_last_sent"] = today
                        self._save_config()

    @_minute_tick.before_loop
    async def _before_minute_tick(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_daily_leetcode(self, guild_id: int, cfg: dict) -> None:
        channel = self.bot.get_channel(cfg["leetcode_channel"])
        if not channel:
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
            url = f"https://leetcode.com{link}" if link and not link.startswith("http") else link
            embed = daily_embed(
                title=title,
                url=url or "https://leetcode.com",
                difficulty=difficulty,
                date=challenge.date,
                content=_strip_html(str(content)) if content else None,
                topic_tags=topic_tags,
            )
            if ac_rate is not None:
                embed.add_field(name="Acceptance", value=f"{float(ac_rate):.1f}%", inline=True)
            await channel.send(content="**Daily LeetCode Challenge**", embed=embed)
            logger.info("Sent daily LeetCode to guild %s", guild_id)
        except Exception as e:
            logger.error("Failed to send daily LeetCode to guild %s: %s", guild_id, e)

    async def _send_news_briefing(self, guild_id: int, cfg: dict) -> None:
        channel = self.bot.get_channel(cfg["news_channel"])
        if not channel:
            return
        news_service = getattr(self.bot, "news_service", None)
        if not news_service:
            return
        try:
            items = await news_service.get_latest(limit=5)
            lines = []
            for i, item in enumerate(items, 1):
                lines.append(f"**{i}.** [{item.title}]({item.link})")
            embed = discord.Embed(
                title="Morning News Briefing",
                description="\n".join(lines) or "No news available.",
                color=discord.Color.blue(),
            )
            await channel.send(embed=embed)
            logger.info("Sent news briefing to guild %s", guild_id)
        except Exception as e:
            logger.error("Failed to send news briefing to guild %s: %s", guild_id, e)

    # -- Alert checker ---------------------------------------------------------

    @tasks.loop(minutes=5)
    async def _alert_check(self) -> None:
        alert_service = getattr(self.bot, "alert_service", None)
        stock_service = getattr(self.bot, "stock_service", None)
        if not alert_service:
            return

        triggered_reminders = alert_service.check_reminder_alerts()
        for alert in triggered_reminders:
            await self._dm_user(
                alert["user_id"],
                f"**Reminder:** {alert['config'].get('message', 'Due now!')}",
            )

        if stock_service:
            symbols = alert_service.get_unique_symbols()
            if symbols:
                prices: dict[str, float] = {}
                for sym in symbols:
                    p = await stock_service.get_price(sym)
                    if p is not None:
                        prices[sym] = p
                triggered_prices = alert_service.check_price_alerts(prices)
                for alert in triggered_prices:
                    cfg = alert["config"]
                    await self._dm_user(
                        alert["user_id"],
                        f"**Price Alert:** {cfg['symbol']} is now "
                        f"${alert['current_price']:,.2f} "
                        f"({cfg['direction']} ${cfg['target']:,.2f})",
                    )

    @_alert_check.before_loop
    async def _before_alert_check(self) -> None:
        await self.bot.wait_until_ready()

    async def _dm_user(self, user_id: int, message: str) -> None:
        try:
            user = await self.bot.fetch_user(user_id)
            embed = discord.Embed(description=message, color=discord.Color.gold())
            await user.send(embed=embed)
        except Exception as e:
            logger.warning("Failed to DM user %s: %s", user_id, e)

    # -- Slash commands to configure schedules ---------------------------------

    @schedule_group.command(name="leetcode", description="Set up daily LeetCode challenge notifications")
    @commands.has_permissions(manage_channels=True)
    async def setup_leetcode(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, description="Channel to post in"),
        hour: discord.Option(int, description="Hour (0-23 UTC)", min_value=0, max_value=23, required=False) = None,
        minute: discord.Option(int, description="Minute (0-59 UTC)", min_value=0, max_value=59, required=False) = None,
    ) -> None:
        h = hour if hour is not None else config.DAILY_NOTIFY_HOUR
        m = minute if minute is not None else config.DAILY_NOTIFY_MINUTE
        cfg = self._guild_configs.setdefault(ctx.guild_id, {})
        cfg.update(leetcode_channel=channel.id, leetcode_hour=h, leetcode_minute=m, leetcode_enabled=True)
        self._save_config()
        await ctx.respond(embed=discord.Embed(
            title="Daily LeetCode Enabled",
            description=f"Daily challenge will be posted in {channel.mention} at **{h:02d}:{m:02d} UTC**.",
            color=discord.Color.green(),
        ))

    @schedule_group.command(name="news", description="Set up daily news briefing notifications")
    @commands.has_permissions(manage_channels=True)
    async def setup_news(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, description="Channel to post in"),
        hour: discord.Option(int, description="Hour (0-23 UTC)", min_value=0, max_value=23, required=False) = 7,
        minute: discord.Option(int, description="Minute (0-59 UTC)", min_value=0, max_value=59, required=False) = 0,
    ) -> None:
        cfg = self._guild_configs.setdefault(ctx.guild_id, {})
        cfg.update(news_channel=channel.id, news_hour=hour, news_minute=minute, news_enabled=True)
        self._save_config()
        await ctx.respond(embed=discord.Embed(
            title="News Briefing Enabled",
            description=f"Daily news will be posted in {channel.mention} at **{hour:02d}:{minute:02d} UTC**.",
            color=discord.Color.green(),
        ))

    @schedule_group.command(name="stop", description="Stop a scheduled notification")
    @commands.has_permissions(manage_channels=True)
    async def stop(
        self,
        ctx: discord.ApplicationContext,
        notification: discord.Option(
            str,
            description="Which notification to stop",
            choices=[
                discord.OptionChoice("LeetCode Daily", "leetcode"),
                discord.OptionChoice("News Briefing", "news"),
            ],
        ),
    ) -> None:
        cfg = self._guild_configs.get(ctx.guild_id, {})
        key = f"{notification}_enabled"
        if not cfg.get(key):
            await ctx.respond(embed=discord.Embed(
                title="Not Active",
                description=f"{notification.title()} notifications are not enabled.",
                color=discord.Color.orange(),
            ))
            return
        cfg[key] = False
        self._save_config()
        await ctx.respond(embed=discord.Embed(
            title="Notifications Disabled",
            description=f"{notification.title()} notifications have been stopped.",
            color=discord.Color.red(),
        ))

    @schedule_group.command(name="status", description="Check scheduled notification settings")
    async def status(self, ctx: discord.ApplicationContext) -> None:
        cfg = self._guild_configs.get(ctx.guild_id, {})
        embed = discord.Embed(title="Scheduled Notifications", color=discord.Color.blue())
        if cfg.get("leetcode_enabled"):
            ch = self.bot.get_channel(cfg.get("leetcode_channel", 0))
            ch_str = ch.mention if ch else "unknown"
            embed.add_field(
                name="LeetCode Daily",
                value=f"{ch_str} at {cfg.get('leetcode_hour', 8):02d}:{cfg.get('leetcode_minute', 0):02d} UTC",
                inline=False,
            )
        else:
            embed.add_field(name="LeetCode Daily", value="Disabled", inline=False)
        if cfg.get("news_enabled"):
            ch = self.bot.get_channel(cfg.get("news_channel", 0))
            ch_str = ch.mention if ch else "unknown"
            embed.add_field(
                name="News Briefing",
                value=f"{ch_str} at {cfg.get('news_hour', 7):02d}:{cfg.get('news_minute', 0):02d} UTC",
                inline=False,
            )
        else:
            embed.add_field(name="News Briefing", value="Disabled", inline=False)
        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    bot.add_cog(SchedulerCog(bot))
